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
    chunk_tables,
)

# ---------------------------------------------------------------------------
# chunk_tables utility tests (unchanged)
# ---------------------------------------------------------------------------


class TestChunkTables:
    def test_empty_list(self):
        assert chunk_tables([], max_size=15) == []

    def test_single_batch_under_limit(self):
        tables = list(range(10))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 1
        assert len(batches[0]) == 10

    def test_exact_batch_size(self):
        tables = list(range(15))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 1
        assert len(batches[0]) == 15

    def test_even_split_two_batches(self):
        # 16 items -> 16 / 15 = 1.something -> 2 batches
        # should be split 8 and 8
        tables = list(range(16))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 2
        assert len(batches[0]) == 8
        assert len(batches[1]) == 8

    def test_uneven_split_remainder(self):
        # 31 items -> 31 / 15 -> 3 batches? No, ceil(2.06) = 3 batches
        # base_size = 31 // 3 = 10, remainder = 1
        # Batches should be 11, 10, 10
        tables = list(range(31))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 3
        assert len(batches[0]) == 11
        assert len(batches[1]) == 10
        assert len(batches[2]) == 10

        # Verify total items
        assert sum(len(b) for b in batches) == 31


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
