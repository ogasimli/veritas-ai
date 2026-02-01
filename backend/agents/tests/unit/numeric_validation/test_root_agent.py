"""Test cases for the numeric validation agent."""

import os

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
    agent_mode = os.getenv("NUMERIC_VALIDATION_AGENT_MODE", "all")

    if agent_mode == "legacy_pipeline":
        expected_count = 1
        enable_legacy = True
        enable_in_table = False
    elif agent_mode == "in_table_pipeline":
        expected_count = 1
        enable_legacy = False
        enable_in_table = True
    else:
        expected_count = 2
        enable_legacy = True
        enable_in_table = True

    assert len(root_agent.sub_agents) == expected_count

    if enable_legacy:
        legacy_pipeline = next(
            a
            for a in root_agent.sub_agents
            if a.name == "LegacyNumericValidationPipeline"
        )
        assert len(legacy_pipeline.sub_agents) == 3

    if enable_in_table:
        in_table_pipeline = next(
            a for a in root_agent.sub_agents if a.name == "InTableVerificationPipeline"
        )
        assert in_table_pipeline.name == "InTableVerificationPipeline"


@pytest.mark.asyncio
async def test_extractor_basic_run():
    """Verify the agent can be initialized in a runner."""
    runner = InMemoryRunner(agent=root_agent)
    assert runner.agent.name == "numeric_validation"
