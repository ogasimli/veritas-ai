"""Unit tests for LogicConsistencyReviewer callbacks, agent factory, and wiring."""

from unittest.mock import MagicMock

import pytest
from google.adk.agents import LlmAgent
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.logic_consistency.sub_agents.reviewer.agent import (
    _create_reviewer_agent,
    _prepare_work_items,
    reviewer_agent,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.logic_consistency.sub_agents.reviewer.callbacks import (
    strip_injected_context,
)


# --- Helper ---


def _make_content(role: str, texts: list[str]) -> types.Content:
    """Build a Content object with the given role and text parts."""
    return types.Content(
        role=role,
        parts=[types.Part(text=t) for t in texts],
    )


def _make_findings(n: int) -> list[dict]:
    """Generate n dummy finding dicts."""
    return [
        {
            "fsli_name": f"FSLI_{i}",
            "claim": f"claim {i}",
            "contradiction": f"contradiction {i}",
            "reasoning": f"reasoning {i}",
            "severity": "high",
            "source_refs": [f"ref_{i}"],
        }
        for i in range(n)
    ]


# --- strip_injected_context Tests ---


class TestStripInjectedContext:
    """Test the before_model_callback that removes 'For context:' contents."""

    def test_removes_for_context_content(self):
        """Should remove content where a part has text 'For context:'."""
        llm_request = LlmRequest(
            contents=[
                _make_content("user", ["For context:", "[Aggregator] said: ..."]),
                _make_content("user", ["Analyze the document"]),
            ]
        )
        strip_injected_context(MagicMock(), llm_request)

        assert len(llm_request.contents) == 1
        assert llm_request.contents[0].parts[0].text == "Analyze the document"

    def test_preserves_non_context_content(self):
        """Should keep contents that don't contain 'For context:'."""
        contents = [
            _make_content("user", ["Please review these findings"]),
            _make_content("model", ["Here are my results"]),
        ]
        llm_request = LlmRequest(contents=list(contents))
        strip_injected_context(MagicMock(), llm_request)

        assert len(llm_request.contents) == 2

    def test_removes_multiple_for_context_entries(self):
        """Should remove all 'For context:' contents, not just the first."""
        llm_request = LlmRequest(
            contents=[
                _make_content("user", ["For context:", "[Agent1] said: ..."]),
                _make_content("user", ["For context:", "[Agent2] said: ..."]),
                _make_content("user", ["Actual input"]),
            ]
        )
        strip_injected_context(MagicMock(), llm_request)

        assert len(llm_request.contents) == 1
        assert llm_request.contents[0].parts[0].text == "Actual input"

    def test_ignores_model_role_with_for_context(self):
        """Should only strip user-role contents, not model-role."""
        llm_request = LlmRequest(
            contents=[
                _make_content("model", ["For context:", "some model output"]),
                _make_content("user", ["input"]),
            ]
        )
        strip_injected_context(MagicMock(), llm_request)

        assert len(llm_request.contents) == 2

    def test_handles_empty_contents(self):
        """Should handle empty contents list without error."""
        llm_request = LlmRequest(contents=[])
        strip_injected_context(MagicMock(), llm_request)

        assert llm_request.contents == []

    def test_for_context_as_non_first_part(self):
        """Should detect 'For context:' even if it's not the first part."""
        llm_request = LlmRequest(
            contents=[
                _make_content("user", ["preamble", "For context:", "[Agent] said: data"]),
            ]
        )
        strip_injected_context(MagicMock(), llm_request)

        assert len(llm_request.contents) == 0

    def test_partial_match_not_stripped(self):
        """Should not strip content where text merely contains 'For context:'."""
        llm_request = LlmRequest(
            contents=[
                _make_content("user", ["For context: see the report below"]),
            ]
        )
        strip_injected_context(MagicMock(), llm_request)

        # "For context: see the report below" != "For context:" (exact match)
        assert len(llm_request.contents) == 1

    def test_content_with_none_parts_preserved(self):
        """Should preserve content where parts is None."""
        content = types.Content(role="user", parts=None)
        llm_request = LlmRequest(contents=[content])
        strip_injected_context(MagicMock(), llm_request)

        assert len(llm_request.contents) == 1


# --- _prepare_work_items Tests ---


class TestPrepareWorkItems:
    """Test the _prepare_work_items callback."""

    def test_returns_empty_when_no_detector_output(self):
        assert _prepare_work_items({}) == []

    def test_returns_empty_when_no_findings(self):
        state = {"logic_consistency_detector_output": {"findings": []}}
        assert _prepare_work_items(state) == []

    def test_returns_empty_when_findings_key_missing(self):
        state = {"logic_consistency_detector_output": {}}
        assert _prepare_work_items(state) == []

    def test_chunks_findings_into_batches_of_3(self):
        findings = _make_findings(7)
        state = {"logic_consistency_detector_output": {"findings": findings}}
        batches = _prepare_work_items(state)

        assert len(batches) == 3
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 1

    def test_single_batch_when_fewer_than_batch_size(self):
        findings = _make_findings(2)
        state = {"logic_consistency_detector_output": {"findings": findings}}
        batches = _prepare_work_items(state)

        assert len(batches) == 1
        assert len(batches[0]) == 2

    def test_exact_batch_size(self):
        findings = _make_findings(3)
        state = {"logic_consistency_detector_output": {"findings": findings}}
        batches = _prepare_work_items(state)

        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_handles_pydantic_detector_output(self):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"findings": _make_findings(2)}
        state = {"logic_consistency_detector_output": mock_output}

        batches = _prepare_work_items(state)

        mock_output.model_dump.assert_called_once()
        assert len(batches) == 1


# --- _create_reviewer_agent Tests ---


class TestCreateReviewerAgent:
    """Test the _create_reviewer_agent callback."""

    def test_returns_llm_agent(self):
        batch = _make_findings(2)
        agent = _create_reviewer_agent(0, batch, "test_key")
        assert isinstance(agent, LlmAgent)

    def test_agent_name_includes_index(self):
        agent = _create_reviewer_agent(3, _make_findings(1), "key")
        assert agent.name == "LogicConsistencyReviewerBatch_3"

    def test_uses_provided_output_key(self):
        agent = _create_reviewer_agent(0, _make_findings(1), "FanOut_item_0")
        assert agent.output_key == "FanOut_item_0"

    def test_include_contents_is_none(self):
        agent = _create_reviewer_agent(0, _make_findings(1), "key")
        assert agent.include_contents == "none"

    def test_before_model_callback_is_strip_injected_context(self):
        agent = _create_reviewer_agent(0, _make_findings(1), "key")
        assert agent.before_model_callback is strip_injected_context

    def test_instruction_contains_batch_findings(self):
        batch = [{"fsli_name": "Revenue", "claim": "test claim"}]
        agent = _create_reviewer_agent(0, batch, "key")
        assert "Revenue" in agent.instruction
        assert "test claim" in agent.instruction

    def test_instruction_does_not_contain_other_findings(self):
        """Instruction should only contain the batch findings, not all findings."""
        batch = [{"fsli_name": "Revenue", "claim": "batch claim"}]
        agent = _create_reviewer_agent(0, batch, "key")
        assert "batch claim" in agent.instruction
        # Other findings not in this batch should not appear
        assert "other_fsli" not in agent.instruction


# --- FanOutAgent Wiring Tests ---


class TestFanOutAgentWiring:
    """Test the module-level FanOutAgent instance configuration."""

    def test_agent_name(self):
        assert reviewer_agent.name == "LogicConsistencyReviewer"

    def test_output_key(self):
        assert reviewer_agent.config.output_key == "logic_consistency_reviewer_output"

    def test_results_field(self):
        assert reviewer_agent.config.results_field == "findings"

    def test_batch_size(self):
        assert reviewer_agent.config.batch_size == 3

    def test_empty_message(self):
        assert (
            reviewer_agent.config.empty_message
            == "No detector findings to review."
        )

    def test_callbacks_wired(self):
        assert reviewer_agent.config.prepare_work_items is _prepare_work_items
        assert reviewer_agent.config.create_agent is _create_reviewer_agent

    def test_no_custom_aggregate(self):
        assert reviewer_agent.config.aggregate is None
