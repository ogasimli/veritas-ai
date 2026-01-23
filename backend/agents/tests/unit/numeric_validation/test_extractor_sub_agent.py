"""Tests for ExtractorAgent."""

import dotenv
import pytest

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.extractor import (
    extractor_agent,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.extractor.schema import (
    ExtractorAgentOutput,
)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_extractor_agent_structure():
    """Verify ExtractorAgent configuration."""
    assert extractor_agent.name == "ExtractorAgent"
    assert extractor_agent.model == "gemini-3-flash-preview"
    assert extractor_agent.output_key == "extractor_output"
    assert extractor_agent.output_schema == ExtractorAgentOutput


def test_extractor_output_schema():
    """Verify ExtractorAgentOutput schema."""
    output = ExtractorAgentOutput(fsli_names=["Revenue", "Net Income"])
    assert output.fsli_names == ["Revenue", "Net Income"]
