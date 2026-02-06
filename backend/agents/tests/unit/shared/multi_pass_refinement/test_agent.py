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


@pytest.mark.asyncio
async def test_run_async_flow():
    """Test the full orchestration flow without executing actual agents."""
    config = _create_mock_config()
    agent = MultiPassRefinementAgent(name="TestAgent", config=config)

    # Mock Context
    ctx = MagicMock()
    ctx.session.state = {}

    # Mock Sub-Agents creation and execution
    with (
        patch(
            "veritas_ai_agent.shared.multi_pass_refinement.agent.ParallelAgent"
        ) as MockParallel,
        patch(
            "veritas_ai_agent.shared.multi_pass_refinement.agent.LoopAgent"
        ) as MockLoop,
        patch(
            "veritas_ai_agent.shared.multi_pass_refinement.agent.LlmAgent"
        ) as MockLlm,
    ):
        # Setup Parallel Agent Mock
        parallel_instance = MockParallel.return_value
        parallel_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator(
            []
        )

        # Setup Aggregator Agent Mock
        aggregator_instance = MockLlm.return_value
        aggregator_instance.run_async.side_effect = (
            lambda *args, **kwargs: AsyncIterator([])
        )
        aggregator_instance.output_key = "agg_output"

        # Setup Loop Agent Mock (for chains)
        loop_instance = MockLoop.return_value
        loop_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator([])

        # Run the agent (call implementation directly to skip BaseAgent wrapper issues)
        async for _e in agent._run_async_impl(ctx):
            pass

        # Verify Parallel execution
        MockParallel.assert_called_once()  # Should be called once for all chains
        call_kwargs = MockParallel.call_args[1]
        assert call_kwargs["name"] == "TestAgent_ParallelChains"
        assert len(call_kwargs["sub_agents"]) == 2  # Default N=2

        # Verify Aggregator creation
        MockLlm.assert_called()  # Called for chain passes and aggregator

        # Verify Aggregator execution
        aggregator_instance.run_async.assert_called_once_with(ctx)


@pytest.mark.asyncio
async def test_findings_collection_logic():
    """Verify that findings are correctly collected from state before aggregation."""
    config = _create_mock_config()
    agent = MultiPassRefinementAgent(name="TestAgent", config=config)

    # Mock Context with pre-populated findings (simulating chain execution)
    ctx = MagicMock()
    findings_chain_0 = [{"issue": "error1"}]
    findings_chain_1 = [{"issue": "error2"}]

    ctx.session.state = {
        "chain_0_accumulated_findings": findings_chain_0,
        "chain_1_accumulated_findings": findings_chain_1,
    }

    # Mock internal methods to isolate aggregator logic
    with (
        patch(
            "veritas_ai_agent.shared.multi_pass_refinement.agent.ParallelAgent"
        ) as MockParallel,
        patch("veritas_ai_agent.shared.multi_pass_refinement.agent.LoopAgent"),
        patch(
            "veritas_ai_agent.shared.multi_pass_refinement.agent.LlmAgent"
        ) as MockLlm,
    ):
        parallel_instance = MockParallel.return_value
        parallel_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator(
            []
        )

        aggregator_instance = MockLlm.return_value
        aggregator_instance.run_async.side_effect = (
            lambda *args, **kwargs: AsyncIterator([])
        )

        # Run
        async for _ in agent._run_async_impl(ctx):
            pass

        expected_findings = findings_chain_0 + findings_chain_1
        expected_json = json.dumps(expected_findings, indent=2)

        # Verify one of the LlmAgent calls used the aggregated instruction
        found_aggregator_call = False
        for call in MockLlm.call_args_list:
            kwargs = call.kwargs
            if kwargs.get("name") == "TestAgentAggregator":
                found_aggregator_call = True
                instruction = kwargs.get("instruction")
                assert isinstance(instruction, str)
                assert str(len(expected_json)) in instruction

        assert found_aggregator_call, "Aggregator agent was not created"


def test_model_config_resolution():
    """Test that models are correctly specified in agent configs."""
    with (
        patch(
            "veritas_ai_agent.shared.multi_pass_refinement.agent.LlmAgent"
        ) as MockLlm,
        patch("veritas_ai_agent.shared.multi_pass_refinement.agent.LoopAgent"),
    ):
        # 1. Default model from config
        config = _create_mock_config()
        agent = MultiPassRefinementAgent(name="TestAgent", config=config)
        agent._create_chain_loop(0)
        assert MockLlm.call_args.kwargs["model"] == "gemini-3-pro-preview"

        # 2. Custom chain model
        chain_config = MultiPassRefinementLlmAgentConfig(
            output_schema=MockPassOutput,
            get_instruction=_mock_get_pass_instruction,
            model="custom-chain-model",
        )
        config = _create_mock_config(chain_agent_config=chain_config)
        agent = MultiPassRefinementAgent(name="TestAgent", config=config)
        agent._create_chain_loop(0)
        assert MockLlm.call_args.kwargs["model"] == "custom-chain-model"

        # 3. Custom aggregator model
        agg_config = MultiPassRefinementLlmAgentConfig(
            output_schema=MockAggregatedOutput,
            get_instruction=_mock_get_aggregator_instruction,
            model="custom-agg-model",
        )
        config = _create_mock_config(aggregator_config=agg_config)
        agent = MultiPassRefinementAgent(name="TestAgent", config=config)
        agent._create_aggregator("[]")
        assert MockLlm.call_args.kwargs["model"] == "custom-agg-model"
