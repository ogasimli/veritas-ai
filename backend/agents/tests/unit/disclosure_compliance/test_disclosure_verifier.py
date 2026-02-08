"""Unit tests for DisclosureVerifier callbacks and FanOutAgent wiring."""

import logging
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.disclosure_compliance.sub_agents.verifier.agent import (
    _create_verifier_agent,
    _prepare_work_items,
    disclosure_verifier_agent,
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

    def test_returns_empty_when_no_scanner_output(self):
        """Should return [] when disclosure_scanner_output is missing."""
        result = _prepare_work_items({})
        assert result == []

    def test_returns_empty_when_no_applicable_standards(self):
        """Should return [] when applicable_standards is empty."""
        state = {"disclosure_scanner_output": {"applicable_standards": []}}
        result = _prepare_work_items(state)
        assert result == []

    def test_returns_empty_when_applicable_standards_key_missing(self):
        """Should return [] when applicable_standards key is absent."""
        state = {"disclosure_scanner_output": {}}
        result = _prepare_work_items(state)
        assert result == []

    @patch(
        "veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.disclosure_compliance.sub_agents.verifier.agent.load_standard_checklist"
    )
    def test_loads_checklists_for_standards(self, mock_load):
        """Should load checklist for each standard and return tuples."""
        checklist_ias1 = {"name": "IAS 1", "disclosures": [{"id": "A1"}]}
        checklist_ifrs15 = {"name": "IFRS 15", "disclosures": [{"id": "B1"}]}
        mock_load.side_effect = [checklist_ias1, checklist_ifrs15]

        state = {
            "disclosure_scanner_output": {"applicable_standards": ["IAS 1", "IFRS 15"]}
        }
        result = _prepare_work_items(state)

        assert len(result) == 2
        assert result[0] == ("IAS 1", checklist_ias1)
        assert result[1] == ("IFRS 15", checklist_ifrs15)
        assert mock_load.call_count == 2

    @patch(
        "veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.disclosure_compliance.sub_agents.verifier.agent.load_standard_checklist"
    )
    def test_skips_missing_checklist_with_warning(self, mock_load, caplog):
        """Should skip standards without checklists and log a warning."""
        checklist_ias1 = {"name": "IAS 1", "disclosures": [{"id": "A1"}]}
        mock_load.side_effect = [
            checklist_ias1,
            ValueError("Standard 'IFRS 99' not found in checklist."),
        ]

        state = {
            "disclosure_scanner_output": {"applicable_standards": ["IAS 1", "IFRS 99"]}
        }
        with caplog.at_level(logging.WARNING):
            result = _prepare_work_items(state)

        assert len(result) == 1
        assert result[0] == ("IAS 1", checklist_ias1)
        assert "Skipping IFRS 99" in caplog.text

    @patch(
        "veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.disclosure_compliance.sub_agents.verifier.agent.load_standard_checklist"
    )
    def test_all_standards_skipped_returns_empty(self, mock_load, caplog):
        """Should return [] when all standards fail checklist loading."""
        mock_load.side_effect = ValueError("Not found")

        state = {"disclosure_scanner_output": {"applicable_standards": ["IFRS 99"]}}
        with caplog.at_level(logging.WARNING):
            result = _prepare_work_items(state)

        assert result == []
        assert "Skipping IFRS 99" in caplog.text

    def test_handles_pydantic_scanner_output(self):
        """Should call model_dump() on pydantic scanner output."""
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"applicable_standards": []}

        state = {"disclosure_scanner_output": mock_output}
        result = _prepare_work_items(state)

        mock_output.model_dump.assert_called_once()
        assert result == []


# --- _create_verifier_agent Tests ---


class TestCreateVerifierAgent:
    """Test the _create_verifier_agent callback."""

    def test_returns_llm_agent(self):
        """Should return an LlmAgent instance."""
        checklist = {
            "name": "IAS 1",
            "disclosures": [{"id": "A1", "reference": "1p1", "requirement": "test"}],
        }
        agent = _create_verifier_agent(0, ("IAS 1", checklist), "test_output_key")

        assert isinstance(agent, LlmAgent)

    def test_uses_provided_output_key(self):
        """Must use the output_key provided by FanOutAgent, not a custom one."""
        checklist = {"name": "IAS 1", "disclosures": []}
        agent = _create_verifier_agent(0, ("IAS 1", checklist), "FanOut_item_0")

        assert agent.output_key == "FanOut_item_0"

    def test_sanitizes_standard_code_in_name(self):
        """Agent name should sanitize special characters in standard code."""
        checklist = {"name": "IAS 1", "disclosures": []}
        agent = _create_verifier_agent(0, ("IAS 1", checklist), "key")

        assert agent.name == "DisclosureVerifier_IAS_1"

    def test_sanitizes_complex_standard_code(self):
        """Agent name should handle complex standard codes with multiple special chars."""
        checklist = {"name": "IFRS 15/16", "disclosures": []}
        agent = _create_verifier_agent(0, ("IFRS 15/16", checklist), "key")

        assert agent.name == "DisclosureVerifier_IFRS_15_16"

    def test_instruction_contains_checklist_data(self):
        """Instruction should contain the checklist disclosure requirements."""
        checklist = {
            "name": "IAS 1",
            "disclosures": [
                {
                    "id": "A1.1",
                    "reference": "1p10",
                    "requirement": "Present financial statements",
                },
            ],
        }
        agent = _create_verifier_agent(0, ("IAS 1", checklist), "key")

        assert isinstance(agent.instruction, str)
        assert "IAS 1" in agent.instruction
        assert "A1.1" in agent.instruction
        assert "1p10" in agent.instruction
        assert "Present financial statements" in agent.instruction

    def test_instruction_contains_standard_code(self):
        """Instruction should reference the standard code."""
        checklist = {"name": "IFRS 15", "disclosures": []}
        agent = _create_verifier_agent(0, ("IFRS 15", checklist), "key")

        assert isinstance(agent.instruction, str)
        assert "IFRS 15" in agent.instruction


# --- FanOutAgent Wiring Tests ---


class TestFanOutAgentWiring:
    """Test the module-level FanOutAgent instance configuration."""

    def test_agent_name(self):
        assert disclosure_verifier_agent.name == "DisclosureVerifier"

    def test_output_key(self):
        assert disclosure_verifier_agent.config.output_key == "disclosure_all_findings"

    def test_results_field(self):
        assert disclosure_verifier_agent.config.results_field == "findings"

    def test_empty_message(self):
        assert (
            disclosure_verifier_agent.config.empty_message
            == "No applicable standards found to verify."
        )

    def test_callbacks_wired(self):
        assert (
            disclosure_verifier_agent.config.prepare_work_items is _prepare_work_items
        )
        assert disclosure_verifier_agent.config.create_agent is _create_verifier_agent

    def test_no_custom_aggregate(self):
        assert disclosure_verifier_agent.config.aggregate is None

    @pytest.mark.asyncio
    async def test_early_exit_no_standards(self):
        """When no applicable standards, state gets empty findings and event is emitted."""
        ctx = MagicMock()
        ctx.session.state = {
            "disclosure_scanner_output": {"applicable_standards": []},
        }

        events = []
        async for event in disclosure_verifier_agent._run_async_impl(ctx):
            events.append(event)

        assert ctx.session.state["disclosure_all_findings"] == {"findings": []}
        assert len(events) == 1
        assert "No applicable standards" in events[0].content.parts[0].text

    @pytest.mark.asyncio
    @patch(
        "veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.disclosure_compliance.sub_agents.verifier.agent.load_standard_checklist"
    )
    async def test_full_flow_aggregation(self, mock_load):
        """End-to-end: prepare -> create -> execute -> aggregate findings."""
        mock_load.return_value = {
            "name": "IAS 1",
            "disclosures": [{"id": "A1", "reference": "ref", "requirement": "req"}],
        }

        ctx = MagicMock()
        ctx.session.state = {
            "disclosure_scanner_output": {"applicable_standards": ["IAS 1", "IFRS 15"]},
            # Simulate sub-agent outputs (FanOutAgent uses "{name}_item_{i}" keys)
            "DisclosureVerifier_item_0": {
                "findings": [{"standard": "IAS 1", "disclosure_id": "A1"}]
            },
            "DisclosureVerifier_item_1": {
                "findings": [{"standard": "IFRS 15", "disclosure_id": "B1"}]
            },
        }

        with patch(
            "google.adk.agents.base_agent.BaseAgent.run_async",
            return_value=AsyncIterator(),
        ):
            async for _ in disclosure_verifier_agent._run_async_impl(ctx):
                pass

        result = ctx.session.state["disclosure_all_findings"]
        assert "findings" in result
        assert len(result["findings"]) == 2
