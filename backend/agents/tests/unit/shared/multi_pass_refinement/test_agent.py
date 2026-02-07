import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from veritas_ai_agent.shared.multi_pass_refinement.agent import (
    MultiPassRefinementAgent,
)
from veritas_ai_agent.shared.multi_pass_refinement.config import (
    MultiPassRefinementConfig,
    MultiPassRefinementLlmAgentConfig,
)

# --- Test Helpers ---


class MockPassOutput(BaseModel):
    findings: list[dict]


class MockAggregatedOutput(BaseModel):
    final_findings: list[dict]


def _mock_get_pass_instruction(chain_idx: int) -> str:
    """Mock pass instruction callable."""
    return f"Pass Prompt {chain_idx}"


def _mock_extract_findings(output: dict) -> list[dict]:
    """Mock findings extraction callable."""
    return output.get("findings", [])


def _mock_get_aggregator_instruction(all_findings_json: str) -> str:
    """Mock aggregator instruction callable."""
    return f"Agg Prompt {len(all_findings_json)}"


def _create_mock_config(**overrides) -> MultiPassRefinementConfig:
    """Create a mock config with all required fields."""
    # Create default chain and aggregator configs (model defaults to "gemini-3-pro-preview")
    chain_config = MultiPassRefinementLlmAgentConfig(
        output_schema=MockPassOutput,
        get_instruction=_mock_get_pass_instruction,
    )
    aggregator_config = MultiPassRefinementLlmAgentConfig(
        output_schema=MockAggregatedOutput,
        get_instruction=_mock_get_aggregator_instruction,
    )

    defaults = {
        "chain_agent_config": chain_config,
        "aggregator_config": aggregator_config,
        "extract_findings": _mock_extract_findings,
        "n_parallel_chains": 2,
        "m_sequential_passes": 3,
    }
    defaults.update(overrides)
    return MultiPassRefinementConfig(**defaults)


class AsyncIterator:
    """Helper to mock async generator."""

    def __init__(self, seq):
        self.iter = iter(seq)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration from None


# --- Tests ---


def test_initialization_defaults():
    config = _create_mock_config()
    agent = MultiPassRefinementAgent(name="TestAgent", config=config)

    assert agent.name == "TestAgent"
    assert agent.config is not None
    assert agent.config.n_parallel_chains == 2
    assert agent.config.m_sequential_passes == 3
    assert agent.output_key == "testagent_output"


def test_configuration_overrides():
    config = _create_mock_config(
        n_parallel_chains=5,
        m_sequential_passes=1,
    )
    agent = MultiPassRefinementAgent(
        name="TestAgent", config=config, output_key="custom_output"
    )

    assert agent.config is not None
    assert agent.config.n_parallel_chains == 5
    assert agent.config.m_sequential_passes == 1
    assert agent.output_key == "custom_output"


from typing import ClassVar

from google.adk.agents import BaseAgent


class MockAgent(BaseAgent):
    """Mock agent that satisfies Pydantic validation."""

    to_yield: ClassVar[list] = []

    async def _run_async_impl(self, ctx):
        for item in self.to_yield:
            yield item


@pytest.mark.asyncio
async def test_run_async_flow():
    """Test the full orchestration flow without executing actual agents."""
    config = _create_mock_config()

    # Patch execution methods to prevent actual running
    with (
        patch(
            "google.adk.agents.ParallelAgent.run_async", return_value=AsyncIterator([])
        ) as mock_parallel_run,
        patch(
            "google.adk.agents.LlmAgent.run_async", return_value=AsyncIterator([])
        ) as mock_llm_run,
        patch(
            "google.adk.agents.SequentialAgent.run_async",
            return_value=AsyncIterator([]),
        ) as mock_sequential_run,
    ):
        # Initialize Agent (Real classes used, so Pydantic validation runs)
        agent = MultiPassRefinementAgent(name="TestAgent", config=config)

        # Mock Context
        ctx = MagicMock()
        ctx.session.state = {}

        # Run the agent
        async for _e in agent._run_async_impl(ctx):
            pass

        # Verify Parallel execution
        mock_parallel_run.assert_called_once()

        # Verify Aggregator execution
        # LlmAgent is used for Aggregator AND Chain Pass Agents.
        # But ParallelAgent.run_async is mocked to yield nothing, so Chain Pass Agents (inside Parallel)
        # are NEVER run.
        # Thus, LlmAgent.run_async should only be called ONCE (for Aggregator).
        mock_llm_run.assert_called_once()

        # Verify SequentialAgent execution
        # SequentialAgents are inside ParallelAgent. Since ParallelAgent.run_async is mocked,
        # SequentialAgent.run_async should NOT be called.
        mock_sequential_run.assert_not_called()


@pytest.mark.asyncio
async def test_findings_collection_logic():
    """Verify that findings are correctly collected from state before aggregation."""
    config = _create_mock_config()

    with (
        patch(
            "google.adk.agents.ParallelAgent.run_async", return_value=AsyncIterator([])
        ),
        patch(
            "google.adk.agents.LlmAgent.run_async", return_value=AsyncIterator([])
        ) as mock_llm_run,
    ):
        agent = MultiPassRefinementAgent(name="TestAgent", config=config)

        # Mock Context with pre-populated findings (simulating chain execution)
        ctx = MagicMock()
        findings_chain_0 = [{"issue": "error1"}]
        findings_chain_1 = [{"issue": "error2"}]

        ctx.session.state = {
            "chain_0_accumulated_findings": findings_chain_0,
            "chain_1_accumulated_findings": findings_chain_1,
        }

        # Run _run_async_impl to trigger collection logic
        async for _ in agent._run_async_impl(ctx):
            pass

        # 1. Verify findings were collected into state
        expected_findings = findings_chain_0 + findings_chain_1
        assert agent._internal_findings_key in ctx.session.state
        assert ctx.session.state[agent._internal_findings_key] == expected_findings

        # 2. Verify Aggregator Instruction Provider
        mock_llm_run.assert_called_once()
        # Retrieve the aggregator agent instance that run_async was called on
        # But since we patched Class.run_async, 'self' in that call would be the instance.
        # But mock_llm_run is the mock object replacing the method. Use call_args.

        # To get the instruction, we can inspect the agent instance directly
        aggregator = agent.aggregator_agent
        assert aggregator is not None
        instruction_provider = aggregator.instruction

        assert callable(instruction_provider)

        # execute provider with context
        prompt = instruction_provider(ctx)
        assert isinstance(prompt, str)

        expected_json_len = len(json.dumps(expected_findings, indent=2))
        assert str(expected_json_len) in prompt


def test_model_config_resolution():
    """Test that models are correctly specified in agent configs."""
    config = _create_mock_config()

    # 1. Default model
    agent = MultiPassRefinementAgent(name="TestAgent1", config=config)

    # Verify Chain Agents
    assert agent.parallel_agent is not None
    chain_sequence = agent.parallel_agent.sub_agents[0]
    pass_agent = chain_sequence.sub_agents[0]
    assert pass_agent.model == "gemini-3-pro-preview"

    # 2. Custom chain model
    chain_config = MultiPassRefinementLlmAgentConfig(
        output_schema=MockPassOutput,
        get_instruction=_mock_get_pass_instruction,
        model="custom-chain-model",
    )
    config_custom = _create_mock_config(chain_agent_config=chain_config)

    agent = MultiPassRefinementAgent(name="TestAgent2", config=config_custom)
    assert agent.parallel_agent is not None
    chain_sequence = agent.parallel_agent.sub_agents[0]
    pass_agent = chain_sequence.sub_agents[0]
    assert pass_agent.model == "custom-chain-model"

    # 3. Custom aggregator model
    agg_config = MultiPassRefinementLlmAgentConfig(
        output_schema=MockAggregatedOutput,
        get_instruction=_mock_get_aggregator_instruction,
        model="custom-agg-model",
    )
    config_agg = _create_mock_config(aggregator_config=agg_config)

    agent = MultiPassRefinementAgent(name="TestAgent3", config=config_agg)
    assert agent.aggregator_agent is not None
    assert agent.aggregator_agent.model == "custom-agg-model"


def test_chain_unrolling_structure():
    """Verify that chains are unrolled into SequentialAgents with distinct pass agents."""
    config = _create_mock_config(
        n_parallel_chains=1,
        m_sequential_passes=3,
    )
    agent = MultiPassRefinementAgent(name="TestAgent", config=config)

    # Get the single chain sequence
    assert agent.parallel_agent is not None
    assert len(agent.parallel_agent.sub_agents) == 1
    chain_sequence = agent.parallel_agent.sub_agents[0]

    # Verify it is a sequence of 3 agents
    # Note: We can't easily check isinstance(SequentialAgent) if we don't import it,
    # but we can check the number of sub_agents.
    assert len(chain_sequence.sub_agents) == 3

    # Verify strict naming and output keys
    # Pass 0
    pass0 = chain_sequence.sub_agents[0]
    assert pass0.name == "TestAgent_Chain0_Pass0"
    assert pass0.output_key == "chain_0_pass_0_output"

    # Pass 1
    pass1 = chain_sequence.sub_agents[1]
    assert pass1.name == "TestAgent_Chain0_Pass1"
    assert pass1.output_key == "chain_0_pass_1_output"

    # Pass 2
    pass2 = chain_sequence.sub_agents[2]
    assert pass2.name == "TestAgent_Chain0_Pass2"
    assert pass2.output_key == "chain_0_pass_2_output"
