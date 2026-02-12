import json

from google.adk.agents import LlmAgent

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.agent import (
    _create_check_fan_out_agent,
    _prepare_work_items,
    create_horizontal_check_agent,
    create_vertical_check_agent,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.schema import (
    HorizontalVerticalCheckAgentOutput,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.utils import (
    _grid_cell_count,
    chunk_tables,
)

# ---------------------------------------------------------------------------
# _grid_cell_count helper tests
# ---------------------------------------------------------------------------


class TestGridCellCount:
    def test_valid_grid(self):
        table = {"grid": [["a", "b", "c"], ["d", "e", "f"]]}
        assert _grid_cell_count(table) == 6

    def test_single_row_grid(self):
        table = {"grid": [["x", "y"]]}
        assert _grid_cell_count(table) == 2

    def test_empty_grid_returns_one(self):
        assert _grid_cell_count({"grid": []}) == 1

    def test_missing_grid_key_returns_one(self):
        assert _grid_cell_count({"data": [[1, 2]]}) == 1

    def test_none_grid_returns_one(self):
        assert _grid_cell_count({"grid": None}) == 1

    def test_non_dict_input_returns_one(self):
        assert _grid_cell_count(42) == 1
        assert _grid_cell_count("hello") == 1

    def test_grid_not_a_list_returns_one(self):
        assert _grid_cell_count({"grid": "not a list"}) == 1

    def test_ragged_rows(self):
        table = {"grid": [["a"], ["b", "c", "d"]]}
        assert _grid_cell_count(table) == 4

    def test_non_list_rows_skipped(self):
        """Non-list rows inside grid are silently skipped."""
        table = {"grid": [[1, 2], None, [3, 4]]}
        assert _grid_cell_count(table) == 4


# ---------------------------------------------------------------------------
# chunk_tables utility tests (LPT greedy)
# ---------------------------------------------------------------------------


class TestChunkTables:
    def test_empty_list(self):
        assert chunk_tables([], max_size=15) == []

    def test_single_batch_under_limit(self):
        """All tables fit in one batch when count <= max_size."""
        tables = [{"id": i} for i in range(10)]
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 1
        assert len(batches[0]) == 10

    def test_exact_batch_size(self):
        tables = [{"id": i} for i in range(15)]
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 1
        assert len(batches[0]) == 15

    def test_two_batches_equal_weight(self):
        """16 equal-weight items -> 2 evenly-sized batches."""
        tables = [{"id": i} for i in range(16)]
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 2
        assert sum(len(b) for b in batches) == 16
        # Batches should be within 1 item of each other.
        sizes = [len(b) for b in batches]
        assert max(sizes) - min(sizes) <= 1

    def test_three_batches_total_preserved(self):
        """31 equal-weight items -> 3 batches, total preserved."""
        tables = [{"id": i} for i in range(31)]
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 3
        assert sum(len(b) for b in batches) == 31
        # Each batch should have at most 11 items (ceil(31/3))
        for b in batches:
            assert len(b) <= 11

    def test_no_batch_exceeds_max_size(self):
        """No batch should ever contain more than max_size tables."""
        tables = [{"id": i} for i in range(45)]
        batches = chunk_tables(tables, max_size=15)
        for b in batches:
            assert len(b) <= 15

    def test_no_batch_exceeds_max_size_skewed_weights(self):
        """max_size must hold even when one table dominates total weight."""
        heavy = [{"id": 0, "grid": [list(range(100))] * 100}]  # 10000 cells
        light = [{"id": i + 1} for i in range(16)]  # 1 cell each
        tables = heavy + light  # 17 total -> 2 batches
        batches = chunk_tables(tables, max_size=15)
        for b in batches:
            assert len(b) <= 15, f"Batch has {len(b)} items, exceeds max_size=15"


class TestChunkTablesLPTBalancing:
    """Tests specific to the LPT greedy load-balancing behavior."""

    def test_imbalance_reduced(self):
        """Large and small tables are spread across batches, not clumped."""
        # 4 big tables (100 cells each) + 12 small tables (1 cell each) = 16
        # -> 2 batches.  LPT should put 2 big + some small in each batch.
        tables = [{"id": i, "grid": [list(range(10))] * 10} for i in range(4)] + [
            {"id": i + 4} for i in range(12)
        ]
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 2

        def batch_weight(batch):
            return sum(_grid_cell_count(t) for t in batch)

        w0, w1 = batch_weight(batches[0]), batch_weight(batches[1])
        # Both batches should be close in weight.  Sequential split would
        # put all 4 big tables in batch 0 (weight 400+4) vs batch 1 (weight 8).
        assert abs(w0 - w1) <= max(w0, w1) * 0.25  # within 25%

    def test_document_order_preserved_within_batch(self):
        """Tables within each batch maintain their original input order."""
        tables = [{"id": i, "grid": [list(range(i + 1))]} for i in range(20)]
        batches = chunk_tables(tables, max_size=15)
        for batch in batches:
            ids = [t["id"] for t in batch]
            assert ids == sorted(ids), f"Batch not in document order: {ids}"

    def test_equal_weight_fallback(self):
        """When all tables have weight 1, distribution still works correctly."""
        tables = list(range(16))  # plain ints, weight=1 each
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 2
        assert sum(len(b) for b in batches) == 16
        sizes = [len(b) for b in batches]
        assert max(sizes) - min(sizes) <= 1

    def test_tie_breaking_lowest_index(self):
        """When batches have equal weight, the table goes to the lower index."""
        # 2 identical tables -> 2 batches (max_size=1).
        tables = [{"id": 0, "grid": [["a"]]}, {"id": 1, "grid": [["b"]]}]
        batches = chunk_tables(tables, max_size=1)
        assert len(batches) == 2
        # First table should be in batch 0, second in batch 1.
        assert batches[0][0]["id"] == 0
        assert batches[1][0]["id"] == 1

    def test_single_heavy_table_among_light(self):
        """LPT fills the lighter batch until it catches up to the heavy one."""
        # heavy=10 cells, 15 light=1 cell each.  After 10 light tables land in
        # batch 1, both batches tie at 10 — so subsequent items start going to
        # batch 0, sharing it with the heavy table.
        heavy = {"id": 0, "grid": [list(range(10))]}  # 10 cells
        light = [{"id": i + 1} for i in range(15)]  # 15 tables, 1 cell each
        tables = [heavy, *light]  # 16 total -> 2 batches
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 2
        assert all(len(b) > 0 for b in batches)
        # The heavy table's batch should also contain light tables.
        heavy_batch = next(b for b in batches if any(t.get("id") == 0 for t in b))
        assert len(heavy_batch) > 1, (
            "Heavy table should share its batch with light tables"
        )


# ---------------------------------------------------------------------------
# _prepare_work_items tests
# ---------------------------------------------------------------------------


class TestPrepareWorkItems:
    def test_empty_state_returns_empty(self):
        """No extracted_tables key defaults to empty list."""
        assert _prepare_work_items({}) == []

    def test_empty_list_returns_empty(self):
        assert _prepare_work_items({"extracted_tables": []}) == []

    def test_empty_json_string_returns_empty(self):
        assert _prepare_work_items({"extracted_tables": "[]"}) == []

    def test_invalid_json_string_returns_empty(self):
        assert _prepare_work_items({"extracted_tables": "not json"}) == []

    def test_dict_envelope_with_tables_key(self):
        """Dict with 'tables' key is unwrapped."""
        tables = [{"table_index": 0}, {"table_index": 1}]
        result = _prepare_work_items({"extracted_tables": {"tables": tables}})
        # 2 tables < 15 -> single batch
        assert len(result) == 1
        assert result[0] == tables

    def test_dict_envelope_without_tables_key(self):
        """Dict without 'tables' key returns empty."""
        assert _prepare_work_items({"extracted_tables": {"other": [1, 2]}}) == []

    def test_list_envelope(self):
        """Plain list of tables is used directly."""
        tables = [{"table_index": i} for i in range(3)]
        result = _prepare_work_items({"extracted_tables": tables})
        assert len(result) == 1
        assert result[0] == tables

    def test_json_string_parsed(self):
        """JSON string is parsed before processing."""
        tables = [{"table_index": 0}]
        state = {"extracted_tables": json.dumps(tables)}
        result = _prepare_work_items(state)
        assert len(result) == 1
        assert result[0] == tables

    def test_chunking_applied(self):
        """Tables exceeding max_size are chunked."""
        tables = [{"table_index": i} for i in range(20)]
        result = _prepare_work_items({"extracted_tables": tables})
        # 20 tables / max 15 -> 2 batches of 10
        assert len(result) == 2
        assert sum(len(b) for b in result) == 20


# ---------------------------------------------------------------------------
# _create_agent callback tests (via _create_check_fan_out_agent)
# ---------------------------------------------------------------------------


class TestCreateAgent:
    def _get_create_agent(self):
        """Get the _create_agent closure from a FanOutAgent."""
        agent = _create_check_fan_out_agent(
            "TestCheck",
            "Instruction with {extracted_tables} placeholder",
            "test_output",
        )
        assert agent.config is not None
        return agent.config.create_agent

    def test_returns_llm_agent(self):
        create_agent = self._get_create_agent()
        batch = [{"table_index": 0, "data": [["a", "b"]]}]
        agent = create_agent(0, batch, "test_key")
        assert isinstance(agent, LlmAgent)

    def test_output_key_passed_through(self):
        """The output_key provided by FanOutAgent is used directly."""
        create_agent = self._get_create_agent()
        batch = [{"table_index": 0}]
        agent = create_agent(0, batch, "TestCheck_item_0")
        assert agent.output_key == "TestCheck_item_0"

    def test_instruction_replacement(self):
        """Instruction template has {extracted_tables} replaced with batch JSON."""
        create_agent = self._get_create_agent()
        batch = [{"table_index": 0}]
        agent = create_agent(0, batch, "key")

        expected_json = json.dumps({"tables": batch}, indent=2)
        assert expected_json in agent.instruction

    def test_agent_name_includes_index(self):
        create_agent = self._get_create_agent()
        batch = [{"table_index": 0}]
        agent = create_agent(3, batch, "key")
        assert agent.name == "TestCheck_3"

    def test_output_schema(self):
        create_agent = self._get_create_agent()
        batch = [{"table_index": 0}]
        agent = create_agent(0, batch, "key")
        assert agent.output_schema == HorizontalVerticalCheckAgentOutput


# ---------------------------------------------------------------------------
# FanOutAgent wiring tests
# ---------------------------------------------------------------------------


class TestFanOutAgentWiring:
    def test_vertical_agent_config(self):
        agent = create_vertical_check_agent()
        assert agent.name == "VerticalCheckAgent"
        assert agent.config is not None
        assert agent.config.output_key == "vertical_check_output"
        assert agent.config.results_field == "formulas"
        assert agent.config.aggregate is None
        assert agent.config.prepare_work_items is _prepare_work_items

    def test_horizontal_agent_config(self):
        agent = create_horizontal_check_agent()
        assert agent.name == "HorizontalCheckAgent"
        assert agent.config is not None
        assert agent.config.output_key == "horizontal_check_output"
        assert agent.config.results_field == "formulas"
        assert agent.config.aggregate is None
        assert agent.config.prepare_work_items is _prepare_work_items

    def test_create_agent_callback_wired(self):
        """Both agents have a create_agent callback wired."""
        v_agent = create_vertical_check_agent()
        h_agent = create_horizontal_check_agent()
        assert v_agent.config is not None
        assert h_agent.config is not None
        assert callable(v_agent.config.create_agent)
        assert callable(h_agent.config.create_agent)

    def test_vertical_uses_vertical_instruction(self):
        """Vertical agent uses VERTICAL_INSTRUCTION template."""

        agent = create_vertical_check_agent()
        assert agent.config is not None
        sub = agent.config.create_agent(0, [{"table_index": 0}], "key")
        # The instruction should contain vertical-specific content
        assert "Vertical Logic Auditor" in sub.instruction
        # And the placeholder should be replaced
        assert "{extracted_tables}" not in sub.instruction

    def test_horizontal_uses_horizontal_instruction(self):
        """Horizontal agent uses HORIZONTAL_INSTRUCTION template."""

        agent = create_horizontal_check_agent()
        assert agent.config is not None
        sub = agent.config.create_agent(0, [{"table_index": 0}], "key")
        # The instruction should contain horizontal-specific content
        assert "Horizontal Logic Auditor" in sub.instruction
        # And the placeholder should be replaced
        assert "{extracted_tables}" not in sub.instruction
