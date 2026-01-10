"""Test cases for the numeric validation agent."""
import pytest
import dotenv
from google.adk.runners import InMemoryRunner
from agents.numeric_validation.agent import root_agent

@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()

def test_agent_structure():
    """Verify the agent structure and sub-agents."""
    assert root_agent.name == "numeric_validation"
    assert len(root_agent.sub_agents) == 1
    assert root_agent.sub_agents[0].name == "PlannerAgent"

@pytest.mark.asyncio
async def test_planner_basic_run():
    """Verify the agent can be initialized in a runner."""
    runner = InMemoryRunner(agent=root_agent)
    assert runner.agent.name == "numeric_validation"
