"""Test cases for the numeric validation agent."""

import dotenv
import pytest
from google.adk.runners import InMemoryRunner

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation import root_agent


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_agent_structure():
    """Verify the top-level agent is a SequentialAgent with the expected shape:

    TableNamer  ->  ParallelAgent(InTable, CrossTable)  ->  Aggregator
    """
    assert root_agent.name == "NumericValidation"

    # Three sequential stages
    assert len(root_agent.sub_agents) == 3

    table_namer = root_agent.sub_agents[0]
    parallel = root_agent.sub_agents[1]
    aggregator = root_agent.sub_agents[2]

    # Stage 1: table namer
    assert table_namer.name == "TableNamer"

    # Stage 2: parallel fan-out containing in-table and cross-table pipelines
    assert parallel.name == "NumericValidationParallel"
    assert len(parallel.sub_agents) == 2
    parallel_names = {a.name for a in parallel.sub_agents}
    assert "InTablePipeline" in parallel_names
    assert "CrossTablePipeline" in parallel_names

    # Stage 3: aggregator
    assert aggregator.name == "Aggregator"


@pytest.mark.asyncio
async def test_extractor_basic_run():
    """Verify the agent can be initialized in a runner."""
    runner = InMemoryRunner(agent=root_agent)
    assert runner.agent.name == "NumericValidation"
