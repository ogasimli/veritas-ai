"""Integration tests for the full numeric validation pipeline."""

import os

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
    # Number of sub-pipelines depends on env vars
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
        legacy_names = [a.name for a in legacy_pipeline.sub_agents]
        assert "ExtractorAgent" in legacy_names
        assert "FanOutVerifierAgent" in legacy_names
        assert "ReviewerAgent" in legacy_names

    if enable_in_table:
        in_table_pipeline = next(
            a for a in root_agent.sub_agents if a.name == "InTableVerificationPipeline"
        )
        assert in_table_pipeline.name == "InTableVerificationPipeline"
        # TableExtractor + Aggregator
        assert len(in_table_pipeline.sub_agents) == 2


def test_pipeline_can_initialize():
    """Verify pipeline can be loaded into a runner."""
    runner = InMemoryRunner(agent=root_agent, app_name="test")
    assert runner.agent.name == "numeric_validation"
