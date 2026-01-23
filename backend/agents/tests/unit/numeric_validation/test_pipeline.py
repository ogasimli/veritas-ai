"""Integration tests for the full numeric validation pipeline."""

import dotenv
import pytest
from google.adk.runners import InMemoryRunner

from veritas_ai_agent.sub_agents.numeric_validation.agent import root_agent

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_root_agent_structure():
    """Verify complete pipeline structure."""
    assert root_agent.name == "numeric_validation"
    assert len(root_agent.sub_agents) == 3

    agent_names = [a.name for a in root_agent.sub_agents]
    assert "ExtractorAgent" in agent_names
    assert "FanOutVerifierAgent" in agent_names
    assert "ReviewerAgent" in agent_names


def test_pipeline_can_initialize():
    """Verify pipeline can be loaded into a runner."""
    runner = InMemoryRunner(agent=root_agent, app_name="test")
    assert runner.agent.name == "numeric_validation"
