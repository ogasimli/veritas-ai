"""Tests for ReviewerAgent."""

import dotenv
import pytest

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.reviewer import (
    Finding,
    ReviewerAgentOutput,
    reviewer_agent,
)

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_reviewer_agent_structure():
    """Verify ReviewerAgent configuration."""
    assert reviewer_agent.name == "ReviewerAgent"
    assert reviewer_agent.model == "gemini-3-pro-preview"
    assert reviewer_agent.code_executor is not None
    assert reviewer_agent.output_key == "reviewer_output"


def test_finding_schema():
    """Verify Finding schema."""
    finding = Finding(
        fsli_name="Revenue",
        summary="Revenue components do not sum to total. Discrepancy: $100K.",
        severity="high",
        expected_value=1500000.0,
        actual_value=1600000.0,
        discrepancy=100000.0,
        source_refs=["Table 4, Row 12"],
    )
    assert finding.severity == "high"
    assert finding.discrepancy == 100000.0


def test_reviewer_agent_output_schema():
    """Verify ReviewerAgentOutput schema."""
    output = ReviewerAgentOutput(findings=[])
    assert output.findings == []


def test_severity_thresholds():
    """Document severity threshold logic."""
    # These thresholds should match the prompt
    # high: > 5%, medium: 1-5%, low: < 1%
    expected = 1000000
    high_discrepancy = 60000  # 6%
    medium_discrepancy = 30000  # 3%
    low_discrepancy = 5000  # 0.5%

    assert (high_discrepancy / expected) * 100 > 5
    assert 1 < (medium_discrepancy / expected) * 100 < 5
    assert (low_discrepancy / expected) * 100 < 1
