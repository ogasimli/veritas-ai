"""Tests for ExtractorAgent."""

import dotenv
import pytest

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.legacy_numeric_validation.extractor import (
    fsli_extractor_agent,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.legacy_numeric_validation.extractor.schema import (
    LegacyNumericFsliExtractorOutput,
)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_extractor_agent_structure():
    """Verify ExtractorAgent configuration."""
    assert fsli_extractor_agent.name == "LegacyNumericFsliExtractor"
    assert fsli_extractor_agent.model == "gemini-3-flash-preview"
    assert fsli_extractor_agent.output_key == "legacy_numeric_fsli_extractor_output"
    assert fsli_extractor_agent.output_schema == LegacyNumericFsliExtractorOutput


def test_extractor_output_schema():
    """Verify ExtractorAgentOutput schema."""
    output = LegacyNumericFsliExtractorOutput(fsli_names=["Revenue", "Net Income"])
    assert output.fsli_names == ["Revenue", "Net Income"]
