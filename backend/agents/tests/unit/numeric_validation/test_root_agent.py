"""Test cases for the numeric validation agent."""

import dotenv
import pytest
from google.adk.runners import InMemoryRunner

from veritas_ai_agent.sub_agents.numeric_validation import root_agent


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_agent_structure():
    """Verify the agent structure and sub-agents."""
    assert root_agent.name == "numeric_validation"
    assert len(root_agent.sub_agents) == 3
    assert root_agent.sub_agents[0].name == "ExtractorAgent"
    assert root_agent.sub_agents[1].name == "FanOutVerifierAgent"
    assert root_agent.sub_agents[2].name == "ReviewerAgent"


@pytest.mark.asyncio
async def test_extractor_basic_run():
    """Verify the agent can be initialized in a runner."""
    runner = InMemoryRunner(agent=root_agent)
    assert runner.agent.name == "numeric_validation"
