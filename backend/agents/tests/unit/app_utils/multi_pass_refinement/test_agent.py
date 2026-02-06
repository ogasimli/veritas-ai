
import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from pydantic import BaseModel

from veritas_ai_agent.app_utils.multi_pass_refinement.agent import (
    MultiPassRefinementAgent,
    MultiPassRefinementConfig,
    LlmAgentConfig,
)
from veritas_ai_agent.app_utils.multi_pass_refinement.protocols import (
    MultiPassRefinementProtocol,
)


# --- Test Helpers ---

class MockPassOutput(BaseModel):
    findings: list[dict]

class MockAggregatedOutput(BaseModel):
    final_findings: list[dict]

class MockProtocol(MultiPassRefinementProtocol):
    """Mock implementation of the protocol for testing."""
    
    @property
    def pass_output_schema(self):
        return MockPassOutput

    @property
    def aggregated_output_schema(self):
        return MockAggregatedOutput

    @property
    def default_n_parallel(self) -> int:
        return 2

    @property
    def default_m_sequential(self) -> int:
        return 3

    def get_pass_instruction(self, chain_idx: int) -> str:
        return f"Pass Prompt {chain_idx}"

    def extract_findings(self, output: dict) -> list[dict]:
        return output.get("findings", [])

    def get_aggregator_instruction(self, all_findings_json: str) -> str:
        return f"Agg Prompt {len(all_findings_json)}"

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
            raise StopAsyncIteration


# --- Tests ---

def test_initialization_defaults():
    protocol = MockProtocol()
    agent = MultiPassRefinementAgent(
        name="TestAgent",
        protocol=protocol
    )
    
    assert agent.name == "TestAgent"
    assert agent._n_parallel == 2
    assert agent._m_sequential == 3
    assert agent.output_key == "testagent_output"


def test_configuration_overrides():
    protocol = MockProtocol()
    config = MultiPassRefinementConfig(
        n_parallel_chains=5,
        m_sequential_passes=1,
    )
    agent = MultiPassRefinementAgent(
        name="TestAgent",
        protocol=protocol,
        config=config,
        output_key="custom_output"
    )
    
    assert agent._n_parallel == 5
    assert agent._m_sequential == 1
    assert agent.output_key == "custom_output"


@pytest.mark.asyncio
async def test_run_async_flow():
    """Test the full orchestration flow without executing actual agents."""
    protocol = MockProtocol()
    agent = MultiPassRefinementAgent(name="TestAgent", protocol=protocol)
    
    # Mock Context
    ctx = MagicMock()
    ctx.session.state = {}
    
    # Mock Sub-Agents creation and execution
    with patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.ParallelAgent") as MockParallel, \
         patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.LoopAgent") as MockLoop, \
         patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.LlmAgent") as MockLlm:
        
        # Setup Parallel Agent Mock
        parallel_instance = MockParallel.return_value
        parallel_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator([])
        
        # Setup Aggregator Agent Mock
        aggregator_instance = MockLlm.return_value
        aggregator_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator([])
        aggregator_instance.output_key = "agg_output"
        
        # Setup Loop Agent Mock (for chains)
        loop_instance = MockLoop.return_value
        loop_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator([])
        
        # Run the agent (call implementation directly to skip BaseAgent wrapper issues)
        async for e in agent._run_async_impl(ctx):
            pass
        
        # Verify Parallel execution
        MockParallel.assert_called_once() # Should be called once for all chains
        call_kwargs = MockParallel.call_args[1]
        assert call_kwargs["name"] == "TestAgent_ParallelChains"
        assert len(call_kwargs["sub_agents"]) == 2  # Default N=2
        
        # Verify Aggregator creation
        MockLlm.assert_called() # Called for chain passes and aggregator
        
        # Verify Aggregator execution
        aggregator_instance.run_async.assert_called_once_with(ctx)
        

@pytest.mark.asyncio
async def test_findings_collection_logic():
    """Verify that findings are correctly collected from state before aggregation."""
    protocol = MockProtocol()
    agent = MultiPassRefinementAgent(name="TestAgent", protocol=protocol)
    
    # Mock Context with pre-populated findings (simulating chain execution)
    ctx = MagicMock()
    findings_chain_0 = [{"issue": "error1"}]
    findings_chain_1 = [{"issue": "error2"}]
    
    ctx.session.state = {
        "chain_0_accumulated_findings": findings_chain_0,
        "chain_1_accumulated_findings": findings_chain_1
    }
    
    # Mock internal methods to isolate aggregator logic
    with patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.ParallelAgent") as MockParallel, \
         patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.LoopAgent") as MockLoop, \
         patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.LlmAgent") as MockLlm:
         
        parallel_instance = MockParallel.return_value
        parallel_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator([])
        
        aggregator_instance = MockLlm.return_value
        aggregator_instance.run_async.side_effect = lambda *args, **kwargs: AsyncIterator([])
        
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
                # The mock protocol returns "Agg Prompt {len}"
                assert str(len(expected_json)) in instruction
        
        assert found_aggregator_call, "Aggregator agent was not created"


def test_model_config_resolution():
    """Test that models are correctly resolved from config hierarchy."""
    protocol = MockProtocol()
    
    with patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.LlmAgent") as MockLlm, \
         patch("veritas_ai_agent.app_utils.multi_pass_refinement.agent.LoopAgent") as MockLoop:
        
        # 1. Default fallback
        agent = MultiPassRefinementAgent(name="TestAgent", protocol=protocol)
        agent._create_chain_loop(0)
        assert MockLlm.call_args.kwargs['model'] == "gemini-3-pro-preview"
        
        # 2. Chain config override
        chain_config = LlmAgentConfig(model="custom-chain-model")
        config = MultiPassRefinementConfig(chain_agent_config=chain_config)
        agent = MultiPassRefinementAgent(name="TestAgent", protocol=protocol, config=config)
        agent._create_chain_loop(0)
        assert MockLlm.call_args.kwargs['model'] == "custom-chain-model"
        
        # 3. Aggregator config override
        agg_config = LlmAgentConfig(model="custom-agg-model")
        config = MultiPassRefinementConfig(aggregator_config=agg_config)
        agent = MultiPassRefinementAgent(name="TestAgent", protocol=protocol, config=config)
        agent._create_aggregator("[]")
        assert MockLlm.call_args.kwargs['model'] == "custom-agg-model"
