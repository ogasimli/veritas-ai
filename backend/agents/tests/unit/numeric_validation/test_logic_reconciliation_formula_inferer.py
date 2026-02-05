"""Unit tests for LogicReconciliationCheckFanOut agent."""

from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
import veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.logic_reconciliation_check.sub_agents.fan_out.agent as fan_out_module
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.logic_reconciliation_check.sub_agents.fan_out.agent import (
    LogicReconciliationFormulaInferer,
)


class TestLogicReconciliationFormulaInferer:
    """Test the fan-out agent logic."""

    @pytest.mark.asyncio
    async def test_fan_out_filtering(self):
        """Should filter candidate tables based on screener output."""
        ctx = MagicMock()

        # Setup state
        ctx.session.state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [0, 2]
            },
            "extracted_tables": [
                {"table_index": 0, "content": "T0"},
                {"table_index": 1, "content": "T1"},
                {"table_index": 2, "content": "T2"},
            ],
        }

        # Mock ParallelAgent
        with patch.object(fan_out_module, "ParallelAgent") as MockParallel:
            mock_instance = MockParallel.return_value

            async def mock_run_async(context):
                # Simulate sub-agents updating state (pseudo-execution)
                yield "dummy_event"

            mock_instance.run_async = mock_run_async

            agent = LogicReconciliationFormulaInferer()

            # Execute _run_async_impl
            # Note: We need to iterate over the generator
            async for _ in agent._run_async_impl(ctx):
                pass

            # Verify candidate filtering logic (internal variable) is correct.
            # But the variable `candidate_tables` is local.
            # However, `agent._create_table_agent` is called with those tables.
            # Let's verify ParallelAgent calls.

            # Check what sub_agents were passed to ParallelAgent
            _args, kwargs = MockParallel.call_args
            sub_agents = kwargs.get("sub_agents", [])

            # We expect 2 agents (for table 0 and table 2)
            assert len(sub_agents) == 2
            # Names usually contain indexes. But we can't easily check internal properties of LlmAgent here
            # unless we mock _create_table_agent too.

    @pytest.mark.asyncio
    async def test_aggregation(self):
        """Should aggregate outputs from per-table agents."""
        ctx = MagicMock()

        ctx.session.state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": [1]
            },
            "extracted_tables": [{"table_index": 1, "content": "T1"}],
            # Simulate what per-table agents wrote:
            "logic_reconciliation_formula_inferer_table_output_1": {
                "formulas": ["formula1", "formula2"]
            },
        }

        with patch.object(fan_out_module, "ParallelAgent") as MockParallel:
            mock_instance = MockParallel.return_value

            async def mock_run_async(context):
                yield "dummy_event"

            mock_instance.run_async = mock_run_async

            agent = LogicReconciliationFormulaInferer()
            async for _ in agent._run_async_impl(ctx):
                pass

            # Check aggregation result
            output = ctx.session.state.get(
                "logic_reconciliation_formula_inferer_output"
            )
            assert output is not None
            assert "formulas" in output
            assert "formula1" in output["formulas"]
            assert "formula2" in output["formulas"]

    @pytest.mark.asyncio
    async def test_no_candidates(self):
        """Should return empty result without running parallel agent if no candidates."""
        ctx = MagicMock()

        ctx.session.state = {
            "logic_reconciliation_check_screener_output": {
                "candidate_table_indexes": []
            },
            "extracted_tables": [{"table_index": 1, "content": "T1"}],
        }

        with patch.object(fan_out_module, "ParallelAgent") as MockParallel:
            agent = LogicReconciliationFormulaInferer()
            async for _ in agent._run_async_impl(ctx):
                pass

            # ParallelAgent should NOT be initialized
            MockParallel.assert_not_called()

            output = ctx.session.state.get(
                "logic_reconciliation_formula_inferer_output"
            )
            assert output == {"formulas": []}
