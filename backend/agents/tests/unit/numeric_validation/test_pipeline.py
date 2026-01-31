"""Integration tests for the full numeric validation pipeline."""

import dotenv
import pytest
from google.adk.runners import InMemoryRunner

from veritas_ai_agent.sub_agents.numeric_validation import root_agent

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_root_agent_structure():
    """Verify complete pipeline structure."""
    assert root_agent.name == "numeric_validation"
    # Now has 2 sub-pipelines: Legacy and In-Table
    assert len(root_agent.sub_agents) == 2

    # Check Legacy Pipeline sub-agents
    legacy_pipeline = root_agent.sub_agents[0]
    assert legacy_pipeline.name == "LegacyNumericValidationPipeline"
    assert len(legacy_pipeline.sub_agents) == 3

    legacy_names = [a.name for a in legacy_pipeline.sub_agents]
    assert "ExtractorAgent" in legacy_names
    assert "FanOutVerifierAgent" in legacy_names
    assert "ReviewerAgent" in legacy_names

    # Check In-Table Pipeline
    in_table_pipeline = root_agent.sub_agents[1]
    assert in_table_pipeline.name == "InTableVerificationPipeline"


def test_pipeline_can_initialize():
    """Verify pipeline can be loaded into a runner."""
    runner = InMemoryRunner(agent=root_agent, app_name="test")
    assert runner.agent.name == "numeric_validation"
