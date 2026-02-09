"""Test cases for the numeric validation agent."""

import os

import dotenv
import pytest
from google.adk.runners import InMemoryRunner

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation import (
    root_agent,
)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


def test_agent_structure():
    """Verify the top-level agent is a SequentialAgent with the expected shape:

    TableNamer  ->  ParallelAgent(...)  ->  Aggregator

    The parallel stage contents depend on NUMERIC_VALIDATION_AGENT_MODE:
      - "all" (default)          -> InTablePipeline + CrossTablePipeline
      - "in_table_pipeline"      -> InTablePipeline only
      - "cross_table_pipeline"   -> CrossTablePipeline only
    """
    agent_mode = os.getenv("NUMERIC_VALIDATION_AGENT_MODE", "all")

    assert root_agent.name == "NumericValidation"

    # Three sequential stages
    assert len(root_agent.sub_agents) == 3

    table_namer = root_agent.sub_agents[0]
    parallel = root_agent.sub_agents[1]
    aggregator = root_agent.sub_agents[2]

    # Stage 1: table namer
    assert table_namer.name == "TableNamer"

    # Stage 2: parallel fan-out — contents depend on agent mode
    assert parallel.name == "NumericValidationParallel"
    parallel_names = {a.name for a in parallel.sub_agents}

    if agent_mode == "in_table_pipeline":
        assert len(parallel.sub_agents) == 1
        assert "InTablePipeline" in parallel_names
    elif agent_mode == "cross_table_pipeline":
        assert len(parallel.sub_agents) == 1
        assert "CrossTablePipeline" in parallel_names
    else:
        assert len(parallel.sub_agents) == 2
        assert "InTablePipeline" in parallel_names
        assert "CrossTablePipeline" in parallel_names

    # Stage 3: aggregator
    assert aggregator.name == "Aggregator"


@pytest.mark.asyncio
async def test_extractor_basic_run():
    """Verify the agent can be initialized in a runner."""
    runner = InMemoryRunner(agent=root_agent)
    assert runner.agent.name == "NumericValidation"
