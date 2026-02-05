from unittest.mock import MagicMock, patch

import pytest

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.agent import (
    BatchedCheckAgent,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.utils import (
    chunk_tables,
)


class TestChunkTables:
    def test_empty_list(self):
        assert chunk_tables([], max_size=15) == []

    def test_single_batch_under_limit(self):
        tables = list(range(10))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 1
        assert len(batches[0]) == 10

    def test_exact_batch_size(self):
        tables = list(range(15))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 1
        assert len(batches[0]) == 15

    def test_even_split_two_batches(self):
        # 16 items -> 16 / 15 = 1.something -> 2 batches
        # should be split 8 and 8
        tables = list(range(16))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 2
        assert len(batches[0]) == 8
        assert len(batches[1]) == 8

    def test_uneven_split_remainder(self):
        # 31 items -> 31 / 15 -> 3 batches? No, ceil(2.06) = 3 batches
        # base_size = 31 // 3 = 10, remainder = 1
        # Batches should be 11, 10, 10
        tables = list(range(31))
        batches = chunk_tables(tables, max_size=15)
        assert len(batches) == 3
        assert len(batches[0]) == 11
        assert len(batches[1]) == 10
        assert len(batches[2]) == 10

        # Verify total items
        assert sum(len(b) for b in batches) == 31


@pytest.mark.asyncio
class TestBatchedCheckAgent:
    @patch(
        "veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.agent.ParallelAgent"
    )
    @patch(
        "veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.agent.LlmAgent"
    )
    async def test_run_async_impl(self, mock_llm_agent, mock_parallel_agent):
        # Setup context and state
        ctx = MagicMock()
        ctx.session.state = {
            "extracted_tables": {"tables": [{"table_index": 0}, {"table_index": 1}]},
            # Pre-populate sub-agent outputs as if they ran
            "test_output_batch_0": {"formulas": [{"f": 1}]},
        }

        # Mock ParallelAgent run_async to loop through sub-agents
        parallel_runner = MagicMock()
        # parallel_runner.run_async.return_value = [] # Not needed if side_effect is used
        mock_parallel_agent.return_value = parallel_runner

        # Mock async generator for ParallelAgent.run_async using a helper
        async def mock_async_gen(ctx):
            yield "event"

        parallel_runner.run_async.side_effect = mock_async_gen

        agent = BatchedCheckAgent(
            name="TestAgent",
            instruction="test {extracted_tables}",
            output_key="test_output",
        )

        # Run
        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Assertions
        assert len(events) == 1  # Should yield from parallel agent

        # Check LLM sub-agent creation
        # With 2 tables and max 15, should be 1 batch
        assert mock_llm_agent.call_count == 1
        _, kwargs = mock_llm_agent.call_args
        assert kwargs["output_key"] == "test_output_batch_0"

        # Check output aggregation
        assert ctx.session.state["test_output"] == {"formulas": [{"f": 1}]}

    @pytest.mark.asyncio
    async def test_run_async_no_tables(self):
        ctx = MagicMock()
        ctx.session.state = {"extracted_tables": []}

        agent = BatchedCheckAgent(
            name="TestAgent", instruction="test", output_key="test_output"
        )

        async for _event in agent._run_async_impl(ctx):
            pass

        assert ctx.session.state["test_output"] == {"formulas": []}
