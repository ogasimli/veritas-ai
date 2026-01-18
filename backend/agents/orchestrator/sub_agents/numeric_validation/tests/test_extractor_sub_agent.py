"""Tests for ExtractorAgent."""
import pytest
import dotenv
from google.adk.runners import InMemoryRunner
from agents.orchestrator.sub_agents.numeric_validation.sub_agents.extractor import extractor_agent
from agents.orchestrator.sub_agents.numeric_validation.sub_agents.extractor.schema import ExtractorAgentOutput

@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()

def test_extractor_agent_structure():
    """Verify ExtractorAgent configuration."""
    assert extractor_agent.name == "ExtractorAgent"
    assert extractor_agent.model == "gemini-3-pro-preview"
    assert extractor_agent.output_key == "extractor_output"
    assert extractor_agent.output_schema == ExtractorAgentOutput
    assert extractor_agent.planner is not None

def test_extractor_output_schema():
    """Verify ExtractorAgentOutput schema."""
    output = ExtractorAgentOutput(fsli_names=["Revenue", "Net Income"])
    assert output.fsli_names == ["Revenue", "Net Income"]
