"""Unit tests for LogicReconciliationFormulaInferer callbacks and FanOutAgent wiring."""

import json
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.logic_reconciliation_check.sub_agents.fan_out.agent import (
    _create_table_agent,
    _prepare_work_items,
    logic_reconciliation_formula_inferer,
)

# --- Helper ---


class AsyncIterator:
    """Helper to mock async generator."""

    def __init__(self, seq=None):
        self.iter = iter(seq or [])

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration from None


# --- _prepare_work_items Tests ---


class TestPrepareWorkItems:
    """Test the _prepare_work_items callback."""

    def test_filters_candidate_tables(self):
        """Should return only tables matching candidate_table_indexes."""
        state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [0, 2]
            },
            "extracted_tables": [
                {"table_index": 0, "content": "T0"},
                {"table_index": 1, "content": "T1"},
                {"table_index": 2, "content": "T2"},
            ],
        }

        result = _prepare_work_items(state)

        assert len(result) == 2
        assert result[0] == {"table_index": 0, "content": "T0"}
        assert result[1] == {"table_index": 2, "content": "T2"}

    def test_returns_empty_when_no_candidates(self):
        """Should return [] when candidate_table_indexes is empty."""
        state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": []
            },
            "extracted_tables": [{"table_index": 1, "content": "T1"}],
        }

        result = _prepare_work_items(state)

        assert result == []

    def test_returns_empty_when_no_screener_output(self):
        """Should return [] when screener output is missing."""
        state = {
            "extracted_tables": [{"table_index": 0, "content": "T0"}],
        }

        result = _prepare_work_items(state)

        assert result == []

    def test_handles_json_string_tables(self):
        """Should parse extracted_tables when provided as JSON string."""
        state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [1]
            },
            "extracted_tables": json.dumps(
                [
                    {"table_index": 0, "content": "T0"},
                    {"table_index": 1, "content": "T1"},
                ]
            ),
        }

        result = _prepare_work_items(state)

        assert len(result) == 1
        assert result[0] == {"table_index": 1, "content": "T1"}

    def test_handles_dict_with_tables_key(self):
        """Should handle extracted_tables as a dict with 'tables' key."""
        state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [0]
            },
            "extracted_tables": {
                "tables": [
                    {"table_index": 0, "content": "T0"},
                    {"table_index": 1, "content": "T1"},
                ]
            },
        }

        result = _prepare_work_items(state)

        assert len(result) == 1
        assert result[0] == {"table_index": 0, "content": "T0"}

    def test_handles_pydantic_screener_output(self):
        """Should call model_dump() on pydantic screener output."""
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"candidate_table_indexes": [0]}

        state = {
            "logic_reconciliation_check_screener_output": mock_output,
            "extracted_tables": [{"table_index": 0, "content": "T0"}],
        }

        result = _prepare_work_items(state)

        mock_output.model_dump.assert_called_once()
        assert len(result) == 1

    def test_handles_invalid_json_string(self):
        """Should return [] when extracted_tables is invalid JSON."""
        state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [0]
            },
            "extracted_tables": "not valid json",
        }

        result = _prepare_work_items(state)

        assert result == []

    def test_skips_missing_table_indexes(self):
        """Should skip candidate indexes not found in tables_list."""
        state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [0, 5, 99]
            },
            "extracted_tables": [
                {"table_index": 0, "content": "T0"},
                {"table_index": 1, "content": "T1"},
            ],
        }

        result = _prepare_work_items(state)

        assert len(result) == 1
        assert result[0] == {"table_index": 0, "content": "T0"}


# --- _create_table_agent Tests ---


class TestCreateTableAgent:
    """Test the _create_table_agent callback."""

    def test_returns_llm_agent(self):
        """Should return an LlmAgent instance."""
        table = {"table_index": 3, "content": "some data"}
        agent = _create_table_agent(0, table, "test_output_key")

        assert isinstance(agent, LlmAgent)

    def test_agent_name_includes_index(self):
        """Agent name should include the work-item index."""
        table = {"table_index": 3, "content": "some data"}
        agent = _create_table_agent(7, table, "test_output_key")

        assert agent.name == "LogicReconciliationFormulaInfererTableAgent_7"

    def test_uses_provided_output_key(self):
        """Must use the output_key provided by FanOutAgent, not a custom one."""
        table = {"table_index": 0, "content": "data"}
        agent = _create_table_agent(0, table, "FanOut_item_0")

        assert agent.output_key == "FanOut_item_0"

    def test_instruction_contains_table_data(self):
        """Instruction should contain the table data as JSON envelope."""
        table = {"table_index": 2, "content": "test_content"}
        agent = _create_table_agent(0, table, "key")

        # The instruction should contain the envelope JSON
        assert isinstance(agent.instruction, str)
        assert "test_content" in agent.instruction
        assert "tables" in agent.instruction

    def test_wraps_table_in_envelope(self):
        """Should wrap work_item in {'tables': [work_item]} envelope."""
        table = {"table_index": 5, "content": "data"}
        agent = _create_table_agent(0, table, "key")

        expected_envelope = json.dumps({"tables": [table]})
        assert isinstance(agent.instruction, str)
        assert expected_envelope in agent.instruction


# --- FanOutAgent Wiring Tests ---


class TestFanOutAgentWiring:
    """Test the module-level FanOutAgent instance configuration."""

    def test_agent_name(self):
        assert (
            logic_reconciliation_formula_inferer.name
            == "LogicReconciliationFormulaInferer"
        )

    def test_output_key(self):
        assert logic_reconciliation_formula_inferer.config is not None
        assert (
            logic_reconciliation_formula_inferer.config.output_key
            == "logic_reconciliation_formula_inferer_output"
        )

    def test_results_field(self):
        assert logic_reconciliation_formula_inferer.config is not None
        assert logic_reconciliation_formula_inferer.config.results_field == "formulas"

    def test_empty_message(self):
        assert logic_reconciliation_formula_inferer.config is not None
        assert (
            logic_reconciliation_formula_inferer.config.empty_message
            == "No candidate tables for logic reconciliation."
        )

    def test_callbacks_wired(self):
        assert logic_reconciliation_formula_inferer.config is not None
        assert (
            logic_reconciliation_formula_inferer.config.prepare_work_items
            is _prepare_work_items
        )
        assert (
            logic_reconciliation_formula_inferer.config.create_agent
            is _create_table_agent
        )

    @pytest.mark.asyncio
    async def test_early_exit_no_candidates(self):
        """When no candidates, state gets empty formulas and event is emitted."""
        ctx = MagicMock()
        ctx.session.state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": []
            },
            "extracted_tables": [],
        }

        events = []
        async for event in logic_reconciliation_formula_inferer._run_async_impl(ctx):
            events.append(event)

        assert ctx.session.state["logic_reconciliation_formula_inferer_output"] == {
            "formulas": []
        }
        assert len(events) == 1
        assert "No candidate tables" in events[0].content.parts[0].text

    @pytest.mark.asyncio
    async def test_full_flow_aggregation(self):
        """End-to-end: prepare -> create -> execute -> aggregate formulas."""
        ctx = MagicMock()
        ctx.session.state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [0, 2]
            },
            "extracted_tables": [
                {"table_index": 0, "content": "T0"},
                {"table_index": 1, "content": "T1"},
                {"table_index": 2, "content": "T2"},
            ],
            # Simulate sub-agent outputs (FanOutAgent uses "{name}_item_{i}" keys)
            "LogicReconciliationFormulaInferer_item_0": {
                "formulas": [{"target_cell": {"table_index": 0}, "formulas": ["f1"]}]
            },
            "LogicReconciliationFormulaInferer_item_1": {
                "formulas": [{"target_cell": {"table_index": 2}, "formulas": ["f2"]}]
            },
        }

        with patch(
            "google.adk.agents.base_agent.BaseAgent.run_async",
            return_value=AsyncIterator(),
        ):
            async for _ in logic_reconciliation_formula_inferer._run_async_impl(ctx):
                pass

        result = ctx.session.state["logic_reconciliation_formula_inferer_output"]
        assert "formulas" in result
        assert len(result["formulas"]) == 2
