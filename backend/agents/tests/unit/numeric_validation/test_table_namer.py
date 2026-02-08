"""Unit tests for the Table Namer agent callbacks and helpers.

No LLM calls are made.  The tests exercise:
    1. before_agent_callback  - extraction + summary generation
    2. after_agent_callback   - name merging from a mock LLM response
    3. Fallback path          - unparsable LLM output -> default names
    4. Edge cases             - empty tables, single table, index mismatches
"""

from unittest.mock import MagicMock

import pytest

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.table_namer.callbacks import (
    _parse_namer_output,
    after_agent_callback,
    before_agent_callback,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.table_namer.schema import (
    TableNameAssignment,
    TableNamerOutput,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Markdown with two clearly-headed tables.  The real extractor will parse
# these into two grids with floats.
TWO_TABLE_MD = (
    "# Balance Sheet\n\n"
    "| Item | 2024 | 2023 |\n"
    "|------|------|------|\n"
    "| Cash | 4,520 | 3,810 |\n"
    "| Debt | (1,200) | (900) |\n"
    "| **Total** | 3,320 | 2,910 |\n"
    "\n"
    "Some narrative between tables.\n\n"
    "# Note 7 - Receivables\n\n"
    "| Component | Amount |\n"
    "|-----------|--------|\n"
    "| Trade | 8,000 |\n"
    "| Other | 2,300 |\n"
    "| **Total** | 10,300 |\n"
)

SINGLE_TABLE_MD = (
    "| Region | Q1 | Q2 |\n"
    "|--------|-----|-----|\n"
    "| North | 100 | 150 |\n"
    "| South | 200 | 180 |\n"
)


def _mock_ctx(state: dict) -> MagicMock:
    """Return a mock CallbackContext backed by a real dict."""
    ctx = MagicMock()
    ctx.state = state
    return ctx


# ===========================================================================
# 1. before_agent_callback
# ===========================================================================


class TestBeforeAgentCallback:
    """Verify that the callback populates extracted_tables_raw and
    tables_summary_for_naming correctly."""

    @pytest.mark.asyncio
    async def test_two_tables_populates_raw(self):
        state: dict = {"document_markdown": TWO_TABLE_MD}
        await before_agent_callback(_mock_ctx(state))

        raw = state["extracted_tables_raw"]
        assert "tables" in raw
        assert len(raw["tables"]) == 2

    @pytest.mark.asyncio
    async def test_two_tables_indices_sequential(self):
        state: dict = {"document_markdown": TWO_TABLE_MD}
        await before_agent_callback(_mock_ctx(state))

        indices = [t["table_index"] for t in state["extracted_tables_raw"]["tables"]]
        assert indices == [0, 1]

    @pytest.mark.asyncio
    async def test_two_tables_grids_have_content(self):
        state: dict = {"document_markdown": TWO_TABLE_MD}
        await before_agent_callback(_mock_ctx(state))

        tables = state["extracted_tables_raw"]["tables"]
        # Each grid must have at least a header row + 1 data row
        for t in tables:
            assert len(t["grid"]) >= 2
            assert len(t["grid"][0]) >= 2  # at least 2 columns

    @pytest.mark.asyncio
    async def test_missing_markdown_gives_empty_tables(self):
        state: dict = {}  # no document_markdown key
        await before_agent_callback(_mock_ctx(state))

        assert state["extracted_tables_raw"] == {"tables": []}
        # No summary key since we removed it

    @pytest.mark.asyncio
    async def test_empty_markdown_gives_empty_tables(self):
        state: dict = {"document_markdown": ""}
        await before_agent_callback(_mock_ctx(state))

        assert state["extracted_tables_raw"] == {"tables": []}

    @pytest.mark.asyncio
    async def test_single_table_extraction(self):
        state: dict = {"document_markdown": SINGLE_TABLE_MD}
        await before_agent_callback(_mock_ctx(state))

        raw = state["extracted_tables_raw"]
        assert len(raw["tables"]) == 1
        assert raw["tables"][0]["table_index"] == 0


# ===========================================================================
# 2. after_agent_callback — happy path
# ===========================================================================


class TestAfterAgentCallbackHappy:
    """Verify correct merging when the LLM returns valid name assignments."""

    def _raw_state_two_tables(self) -> dict:
        """Pre-populated state as if before_agent_callback already ran."""
        return {
            "extracted_tables_raw": {
                "tables": [
                    {
                        "table_index": 0,
                        "grid": [["Item", "2024"], ["Cash", 4520.0]],
                    },
                    {
                        "table_index": 1,
                        "grid": [["Component", "Amount"], ["Trade", 8000.0]],
                    },
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_merges_names_from_dict_output(self):
        """ADK serialises output_schema as a dict with 'table_names' key."""
        state = self._raw_state_two_tables()
        state["table_namer_output"] = {
            "table_names": [
                {"table_index": 0, "table_name": "Balance Sheet"},
                {"table_index": 1, "table_name": "Note 7 - Receivables"},
            ]
        }

        await after_agent_callback(_mock_ctx(state))

        tables = state["extracted_tables"]["tables"]
        assert len(tables) == 2
        assert tables[0]["table_name"] == "Balance Sheet"
        assert tables[0]["table_index"] == 0
        assert tables[0]["grid"] == [["Item", "2024"], ["Cash", 4520.0]]
        assert tables[1]["table_name"] == "Note 7 - Receivables"

    @pytest.mark.asyncio
    async def test_merges_names_from_pydantic_model(self):
        """If ADK passes the validated Pydantic object directly."""
        state = self._raw_state_two_tables()
        state["table_namer_output"] = TableNamerOutput(
            table_names=[
                TableNameAssignment(table_index=0, table_name="Balance Sheet"),
                TableNameAssignment(table_index=1, table_name="Note 7"),
            ]
        )

        await after_agent_callback(_mock_ctx(state))

        tables = state["extracted_tables"]["tables"]
        assert tables[0]["table_name"] == "Balance Sheet"
        assert tables[1]["table_name"] == "Note 7"

    @pytest.mark.asyncio
    async def test_output_preserves_grid(self):
        """Grid data must pass through untouched."""
        state = self._raw_state_two_tables()
        state["table_namer_output"] = {
            "table_names": [
                {"table_index": 0, "table_name": "A"},
                {"table_index": 1, "table_name": "B"},
            ]
        }

        await after_agent_callback(_mock_ctx(state))

        assert state["extracted_tables"]["tables"][0]["grid"] == [
            ["Item", "2024"],
            ["Cash", 4520.0],
        ]


# ===========================================================================
# 3. Fallback path — unparsable LLM output
# ===========================================================================


class TestAfterAgentCallbackFallback:
    """When the LLM output cannot be parsed, names default to 'Table N'."""

    def _raw_state(self) -> dict:
        return {
            "extracted_tables_raw": {
                "tables": [
                    {"table_index": 0, "grid": [["A"], [1.0]]},
                    {"table_index": 1, "grid": [["B"], [2.0]]},
                    {"table_index": 2, "grid": [["C"], [3.0]]},
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_garbage_string_falls_back(self):
        state = self._raw_state()
        state["table_namer_output"] = "this is not valid json at all"

        await after_agent_callback(_mock_ctx(state))

        names = [t["table_name"] for t in state["extracted_tables"]["tables"]]
        assert names == ["Table 0", "Table 1", "Table 2"]

    @pytest.mark.asyncio
    async def test_none_output_falls_back(self):
        state = self._raw_state()
        state["table_namer_output"] = None

        await after_agent_callback(_mock_ctx(state))

        names = [t["table_name"] for t in state["extracted_tables"]["tables"]]
        assert names == ["Table 0", "Table 1", "Table 2"]

    @pytest.mark.asyncio
    async def test_missing_output_key_falls_back(self):
        """table_namer_output not present in state at all."""
        state = self._raw_state()
        # Deliberately omit table_namer_output

        await after_agent_callback(_mock_ctx(state))

        names = [t["table_name"] for t in state["extracted_tables"]["tables"]]
        assert names == ["Table 0", "Table 1", "Table 2"]

    @pytest.mark.asyncio
    async def test_empty_dict_falls_back(self):
        state = self._raw_state()
        state["table_namer_output"] = {}

        await after_agent_callback(_mock_ctx(state))

        names = [t["table_name"] for t in state["extracted_tables"]["tables"]]
        assert names == ["Table 0", "Table 1", "Table 2"]

    @pytest.mark.asyncio
    async def test_json_object_not_array_falls_back(self):
        """A JSON string that parses but is not an array."""
        state = self._raw_state()
        state["table_namer_output"] = '{"unexpected": "shape"}'

        await after_agent_callback(_mock_ctx(state))

        names = [t["table_name"] for t in state["extracted_tables"]["tables"]]
        assert names == ["Table 0", "Table 1", "Table 2"]

    @pytest.mark.asyncio
    async def test_markdown_fenced_json_parsed(self):
        """A JSON array wrapped in markdown code fences should still parse."""
        state = self._raw_state()
        state["table_namer_output"] = (
            '```json\n[{"table_index": 0, "table_name": "Fenced"}]\n```'
        )

        await after_agent_callback(_mock_ctx(state))

        tables = state["extracted_tables"]["tables"]
        # Index 0 got the name; 1 and 2 fell back
        assert tables[0]["table_name"] == "Fenced"
        assert tables[1]["table_name"] == "Table 1"
        assert tables[2]["table_name"] == "Table 2"


# ===========================================================================
# 4. Edge cases
# ===========================================================================


class TestEdgeCases:
    """Empty tables list, single table, table_index mismatches."""

    @pytest.mark.asyncio
    async def test_empty_tables_list(self):
        """No tables extracted -> extracted_tables is an empty list."""
        state: dict = {
            "extracted_tables_raw": {"tables": []},
            "table_namer_output": {"table_names": []},
        }

        await after_agent_callback(_mock_ctx(state))

        assert state["extracted_tables"] == {"tables": []}

    @pytest.mark.asyncio
    async def test_single_table_named(self):
        state: dict = {
            "extracted_tables_raw": {
                "tables": [
                    {"table_index": 0, "grid": [["X"], [42.0]]},
                ]
            },
            "table_namer_output": {
                "table_names": [{"table_index": 0, "table_name": "Solo Table"}]
            },
        }

        await after_agent_callback(_mock_ctx(state))

        assert len(state["extracted_tables"]["tables"]) == 1
        assert state["extracted_tables"]["tables"][0]["table_name"] == "Solo Table"

    @pytest.mark.asyncio
    async def test_llm_returns_extra_indices_ignored(self):
        """LLM invents a table_index that doesn't exist — it is simply ignored
        because we iterate over raw_tables, not the LLM output."""
        state: dict = {
            "extracted_tables_raw": {
                "tables": [
                    {"table_index": 0, "grid": [["A"], [1.0]]},
                ]
            },
            "table_namer_output": {
                "table_names": [
                    {"table_index": 0, "table_name": "Real"},
                    {"table_index": 99, "table_name": "Ghost"},  # does not exist
                ]
            },
        }

        await after_agent_callback(_mock_ctx(state))

        tables = state["extracted_tables"]["tables"]
        assert len(tables) == 1
        assert tables[0]["table_name"] == "Real"

    @pytest.mark.asyncio
    async def test_llm_missing_some_indices_falls_back(self):
        """LLM only names table 1; table 0 falls back to default."""
        state: dict = {
            "extracted_tables_raw": {
                "tables": [
                    {"table_index": 0, "grid": [["A"], [1.0]]},
                    {"table_index": 1, "grid": [["B"], [2.0]]},
                ]
            },
            "table_namer_output": {
                "table_names": [
                    {"table_index": 1, "table_name": "Only This One"},
                ]
            },
        }

        await after_agent_callback(_mock_ctx(state))

        tables = state["extracted_tables"]["tables"]
        assert tables[0]["table_name"] == "Table 0"  # fallback
        assert tables[1]["table_name"] == "Only This One"

    @pytest.mark.asyncio
    async def test_llm_duplicate_indices_last_wins(self):
        """If the LLM returns two entries for the same index, the later one
        wins because _assignments_to_map iterates sequentially."""
        state: dict = {
            "extracted_tables_raw": {
                "tables": [
                    {"table_index": 0, "grid": [["A"], [1.0]]},
                ]
            },
            "table_namer_output": {
                "table_names": [
                    {"table_index": 0, "table_name": "First"},
                    {"table_index": 0, "table_name": "Second"},
                ]
            },
        }

        await after_agent_callback(_mock_ctx(state))

        assert state["extracted_tables"]["tables"][0]["table_name"] == "Second"


# ===========================================================================
# 5. _parse_namer_output unit tests
# ===========================================================================


class TestParseNamerOutput:
    """Isolated tests for the parsing helper."""

    def test_pydantic_model(self):
        model = TableNamerOutput(
            table_names=[TableNameAssignment(table_index=2, table_name="X")]
        )
        assert _parse_namer_output(model) == {2: "X"}

    def test_dict_with_table_names(self):
        raw = {"table_names": [{"table_index": 0, "table_name": "Y"}]}
        assert _parse_namer_output(raw) == {0: "Y"}

    def test_valid_json_string_array(self):
        raw = '[{"table_index": 1, "table_name": "Z"}]'
        assert _parse_namer_output(raw) == {1: "Z"}

    def test_invalid_json_string_returns_empty(self):
        assert _parse_namer_output("not json") == {}

    def test_none_returns_empty(self):
        assert _parse_namer_output(None) == {}

    def test_integer_returns_empty(self):
        assert _parse_namer_output(42) == {}

    def test_empty_list_string(self):
        assert _parse_namer_output("[]") == {}

    def test_fenced_json_string(self):
        fenced = '```json\n[{"table_index": 3, "table_name": "Fenced"}]\n```'
        assert _parse_namer_output(fenced) == {3: "Fenced"}
