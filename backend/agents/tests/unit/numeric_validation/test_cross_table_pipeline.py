"""Unit tests for the cross-table pipeline components.

Coverage:
    1. ``TestFsliExtractorSchema``          - FsliExtractorOutput validation
    2. ``TestCrossTableBatching``           - FSLI chunking logic
    3. ``TestPrepareWorkItems``             - _prepare_work_items callback
    4. ``TestCreateChunkAgent``             - _create_chunk_agent callback
    5. ``TestAggregate``                    - _aggregate callback (check_type stamping)
    6. ``TestFanOutAgentWiring``            - module-level FanOutAgent configuration
    7. ``TestAfterFanOutCallback``          - after_agent_callback on FanOutAgent
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.cross_table_pipeline.sub_agents.cross_table_fan_out.agent import (
    _aggregate,
    _create_chunk_agent,
    _prepare_work_items,
    cross_table_fan_out_agent,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.cross_table_pipeline.sub_agents.cross_table_fan_out.callbacks import (
    after_fan_out_callback,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.cross_table_pipeline.sub_agents.cross_table_fan_out.chunking import (
    chunk_fsli_list,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.cross_table_pipeline.sub_agents.fsli_extractor.schema import (
    FsliExtractorOutput,
)


# --- Helper ---


class AsyncIterator:
    """Helper to mock async generator."""

    def __init__(self, seq=None):
        self.iter = iter(seq or [])

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration from None


# ===========================================================================
# 1. TestFsliExtractorSchema
# ===========================================================================


class TestFsliExtractorSchema:
    """Pydantic validation round-trips for FsliExtractorOutput."""

    def test_valid_full_output(self):
        out = FsliExtractorOutput(
            primary_fsli=["Total assets", "Net profit"],
            sub_fsli=["Trade receivables", "Interest on lease liabilities"],
        )
        assert out.primary_fsli == ["Total assets", "Net profit"]
        assert out.sub_fsli == ["Trade receivables", "Interest on lease liabilities"]
        assert out.error is None

    def test_empty_lists_are_valid(self):
        out = FsliExtractorOutput(primary_fsli=[], sub_fsli=[])
        assert out.primary_fsli == []
        assert out.sub_fsli == []

    def test_defaults_produce_empty_lists(self):
        out = FsliExtractorOutput()
        assert out.primary_fsli == []
        assert out.sub_fsli == []

    def test_model_dump_round_trip(self):
        original = FsliExtractorOutput(
            primary_fsli=["PPE"],
            sub_fsli=["Leasehold improvements"],
        )
        dumped = original.model_dump()
        restored = FsliExtractorOutput.model_validate(dumped)
        assert restored == original

    def test_extra_error_field_preserved(self):
        """BaseAgentOutput.error field should be settable."""
        from veritas_ai_agent.schemas import AgentError

        err = AgentError(
            agent_name="FsliExtractor",
            error_type="rate_limit",
            error_message="429 hit",
        )
        out = FsliExtractorOutput(error=err)
        assert out.error is not None
        assert out.error.agent_name == "FsliExtractor"
        # Lists default to empty when error occurs
        assert out.primary_fsli == []
        assert out.sub_fsli == []

    def test_only_primary_populated(self):
        out = FsliExtractorOutput(primary_fsli=["Total equity"])
        assert out.primary_fsli == ["Total equity"]
        assert out.sub_fsli == []

    def test_only_sub_populated(self):
        out = FsliExtractorOutput(sub_fsli=["Goodwill amortisation"])
        assert out.primary_fsli == []
        assert out.sub_fsli == ["Goodwill amortisation"]


# ===========================================================================
# 2. TestCrossTableBatching
# ===========================================================================


class TestCrossTableBatching:
    """Pure-function tests for chunk_fsli_list."""

    def test_empty_list_returns_empty(self):
        assert chunk_fsli_list([], 5) == []

    def test_single_fsli_one_chunk(self):
        result = chunk_fsli_list(["Total assets"], 5)
        assert result == [["Total assets"]]

    def test_exact_multiple_of_batch_size(self):
        fslis = [f"FSLI_{i}" for i in range(10)]
        result = chunk_fsli_list(fslis, 5)
        assert len(result) == 2
        assert result[0] == fslis[:5]
        assert result[1] == fslis[5:]

    def test_not_exact_multiple_last_chunk_smaller(self):
        fslis = [f"FSLI_{i}" for i in range(7)]
        result = chunk_fsli_list(fslis, 5)
        assert len(result) == 2
        assert len(result[0]) == 5
        assert len(result[1]) == 2

    def test_batch_size_one(self):
        fslis = ["A", "B", "C"]
        result = chunk_fsli_list(fslis, 1)
        assert result == [["A"], ["B"], ["C"]]

    def test_batch_size_larger_than_list(self):
        fslis = ["A", "B"]
        result = chunk_fsli_list(fslis, 10)
        assert result == [["A", "B"]]

    @patch.dict(os.environ, {"FSLI_BATCH_SIZE": "3"})
    def test_env_configurable_batch_size(self):
        """Reimport to pick up the env var -- but since chunk_fsli_list
        takes batch_size as a parameter, we just call it directly with 3."""
        fslis = [f"FSLI_{i}" for i in range(7)]
        result = chunk_fsli_list(fslis, 3)
        assert len(result) == 3  # 3 + 3 + 1
        assert len(result[2]) == 1

    def test_preserves_order(self):
        fslis = ["Z", "A", "M", "B"]
        result = chunk_fsli_list(fslis, 2)
        assert result == [["Z", "A"], ["M", "B"]]

    def test_large_list_chunking(self):
        fslis = [f"FSLI_{i}" for i in range(100)]
        result = chunk_fsli_list(fslis, 5)
        assert len(result) == 20
        assert all(len(chunk) == 5 for chunk in result)


# ===========================================================================
# 3. TestPrepareWorkItems
# ===========================================================================


class TestPrepareWorkItems:
    """Test the _prepare_work_items callback."""

    def test_combines_primary_and_sub_fsli(self):
        """Should combine primary and sub FSLIs and chunk them."""
        state = {
            "fsli_extractor_output": {
                "primary_fsli": ["Total assets", "Net profit"],
                "sub_fsli": ["Trade receivables"],
            },
            "extracted_tables": {"tables": [{"table_index": 0}]},
        }

        result = _prepare_work_items(state)

        # With 3 FSLIs and batch_size=5 (default), should produce 1 chunk
        assert len(result) == 1
        fsli_batch_json, tables_json = result[0]
        fslis = json.loads(fsli_batch_json)
        assert fslis == ["Total assets", "Net profit", "Trade receivables"]

    def test_returns_empty_when_no_fslis(self):
        """Should return [] when no FSLIs found."""
        state = {
            "fsli_extractor_output": {"primary_fsli": [], "sub_fsli": []},
            "extracted_tables": {"tables": []},
        }

        result = _prepare_work_items(state)

        assert result == []

    def test_returns_empty_when_no_extractor_output(self):
        """Should return [] when extractor output is missing."""
        state = {"extracted_tables": {"tables": []}}

        result = _prepare_work_items(state)

        assert result == []

    def test_handles_pydantic_extractor_output(self):
        """Should call model_dump() on pydantic extractor output."""
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {
            "primary_fsli": ["Revenue"],
            "sub_fsli": [],
        }

        state = {
            "fsli_extractor_output": mock_output,
            "extracted_tables": {"tables": [{"table_index": 0}]},
        }

        result = _prepare_work_items(state)

        mock_output.model_dump.assert_called_once()
        assert len(result) == 1

    def test_work_item_includes_tables_json(self):
        """Each work item should include serialized tables."""
        tables = {"tables": [{"table_index": 0, "grid": [[1, 2]]}]}
        state = {
            "fsli_extractor_output": {
                "primary_fsli": ["Cash"],
                "sub_fsli": [],
            },
            "extracted_tables": tables,
        }

        result = _prepare_work_items(state)

        _, tables_json = result[0]
        assert json.loads(tables_json) == tables

    def test_chunking_with_many_fslis(self):
        """Should produce multiple work items for large FSLI lists."""
        fslis = [f"FSLI_{i}" for i in range(12)]
        state = {
            "fsli_extractor_output": {
                "primary_fsli": fslis[:6],
                "sub_fsli": fslis[6:],
            },
            "extracted_tables": {},
        }

        # Default FSLI_BATCH_SIZE=5, so 12 FSLIs -> 3 chunks (5+5+2)
        result = _prepare_work_items(state)

        assert len(result) == 3
        chunk_0 = json.loads(result[0][0])
        chunk_1 = json.loads(result[1][0])
        chunk_2 = json.loads(result[2][0])
        assert len(chunk_0) == 5
        assert len(chunk_1) == 5
        assert len(chunk_2) == 2

    def test_all_chunks_share_same_tables_json(self):
        """Every work item should have the same tables_json."""
        fslis = [f"FSLI_{i}" for i in range(12)]
        state = {
            "fsli_extractor_output": {
                "primary_fsli": fslis,
                "sub_fsli": [],
            },
            "extracted_tables": {"tables": [{"table_index": 0}]},
        }

        result = _prepare_work_items(state)

        tables_jsons = [item[1] for item in result]
        assert all(t == tables_jsons[0] for t in tables_jsons)

    def test_only_primary_fsli(self):
        """Should work with only primary FSLIs."""
        state = {
            "fsli_extractor_output": {
                "primary_fsli": ["Total equity"],
                "sub_fsli": [],
            },
            "extracted_tables": {},
        }

        result = _prepare_work_items(state)

        assert len(result) == 1
        fslis = json.loads(result[0][0])
        assert fslis == ["Total equity"]

    def test_only_sub_fsli(self):
        """Should work with only sub FSLIs."""
        state = {
            "fsli_extractor_output": {
                "primary_fsli": [],
                "sub_fsli": ["Goodwill"],
            },
            "extracted_tables": {},
        }

        result = _prepare_work_items(state)

        assert len(result) == 1
        fslis = json.loads(result[0][0])
        assert fslis == ["Goodwill"]


# ===========================================================================
# 4. TestCreateChunkAgent
# ===========================================================================


class TestCreateChunkAgent:
    """Test the _create_chunk_agent callback."""

    def test_returns_llm_agent(self):
        """Should return an LlmAgent instance."""
        work_item = ('["Total assets"]', '{"tables": []}')
        agent = _create_chunk_agent(0, work_item, "test_key")

        assert isinstance(agent, LlmAgent)

    def test_agent_name_includes_index(self):
        """Agent name should include the chunk index."""
        work_item = ('["Total assets"]', '{"tables": []}')
        agent = _create_chunk_agent(3, work_item, "test_key")

        assert agent.name == "CrossTableBatch_3"

    def test_uses_provided_output_key(self):
        """Must use the output_key provided by FanOutAgent."""
        work_item = ('["Cash"]', '{"tables": []}')
        agent = _create_chunk_agent(0, work_item, "FanOut_item_0")

        assert agent.output_key == "FanOut_item_0"

    def test_instruction_contains_fsli_and_tables(self):
        """Instruction should contain both FSLI batch and table data."""
        fsli_json = '["Revenue", "Cost of sales"]'
        tables_json = '{"tables": [{"table_index": 0}]}'
        work_item = (fsli_json, tables_json)
        agent = _create_chunk_agent(0, work_item, "key")

        assert "Revenue" in agent.instruction
        assert "Cost of sales" in agent.instruction
        assert "table_index" in agent.instruction


# ===========================================================================
# 5. TestAggregate
# ===========================================================================


class TestAggregate:
    """Test the _aggregate callback that stamps check_type."""

    def test_single_batch_single_formula(self):
        outputs = [
            {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 0, "row_index": 3, "col_index": 1},
                            {"table_index": 1, "row_index": 2, "col_index": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(0, 3, 1) - sum_col(1, 1, 1, 2)"}
                        ],
                    }
                ]
            }
        ]

        result = _aggregate(outputs)

        assert len(result["formulas"]) == 1
        entry = result["formulas"][0]
        assert entry["check_type"] == "cross_table"
        assert entry["actual_value"] is None
        assert len(entry["target_cells"]) == 2

    def test_multiple_batches(self):
        outputs = [
            {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 0, "row_index": 1, "col_index": 1},
                            {"table_index": 2, "row_index": 4, "col_index": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(0,1,1) - cell(2,4,1)"}
                        ],
                    }
                ]
            },
            {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 1, "row_index": 2, "col_index": 2},
                            {"table_index": 3, "row_index": 1, "col_index": 2},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(1,2,2) - cell(3,1,2)"}
                        ],
                    },
                    {
                        "target_cells": [
                            {"table_index": 0, "row_index": 5, "col_index": 1},
                            {"table_index": 1, "row_index": 3, "col_index": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(0,5,1) - sum_col(1,1,1,2)"}
                        ],
                    },
                ]
            },
        ]

        result = _aggregate(outputs)

        assert len(result["formulas"]) == 3
        assert all(
            e["check_type"] == "cross_table" for e in result["formulas"]
        )

    def test_empty_outputs(self):
        result = _aggregate([])
        assert result == {"formulas": []}

    def test_empty_formulas_in_outputs(self):
        outputs = [{"formulas": []}, {"formulas": []}]

        result = _aggregate(outputs)

        assert result == {"formulas": []}

    def test_preserves_inferred_formulas_structure(self):
        """The inferred_formulas list should be preserved as-is."""
        outputs = [
            {
                "formulas": [
                    {
                        "target_cells": [{"table_index": 0, "row_index": 1, "col_index": 1}],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(0,1,1) - cell(1,1,1)"},
                            {"formula": "cell(0,1,1) - sum_col(1,1,1,3)"},
                        ],
                    }
                ]
            }
        ]

        result = _aggregate(outputs)

        entry = result["formulas"][0]
        assert len(entry["inferred_formulas"]) == 2


# ===========================================================================
# 6. TestFanOutAgentWiring
# ===========================================================================


class TestFanOutAgentWiring:
    """Test the module-level FanOutAgent instance configuration."""

    def test_agent_name(self):
        assert cross_table_fan_out_agent.name == "CrossTableFormulaFanOut"

    def test_output_key(self):
        assert cross_table_fan_out_agent.config.output_key == "cross_table_fan_out_output"

    def test_results_field(self):
        assert cross_table_fan_out_agent.config.results_field == "formulas"

    def test_batch_size_sequential(self):
        """batch_size=1 means sequential processing for rate limiting."""
        assert cross_table_fan_out_agent.config.batch_size == 1

    def test_aggregate_callback(self):
        assert cross_table_fan_out_agent.config.aggregate is _aggregate

    def test_empty_message(self):
        assert cross_table_fan_out_agent.config.empty_message == "No FSLIs to analyse; skipping."

    def test_callbacks_wired(self):
        assert cross_table_fan_out_agent.config.prepare_work_items is _prepare_work_items
        assert cross_table_fan_out_agent.config.create_agent is _create_chunk_agent

    @pytest.mark.asyncio
    async def test_early_exit_no_fslis(self):
        """When no FSLIs, state gets empty formulas dict and event is emitted."""
        ctx = MagicMock()
        ctx.session.state = {
            "fsli_extractor_output": {"primary_fsli": [], "sub_fsli": []},
            "extracted_tables": {},
        }

        events = []
        async for event in cross_table_fan_out_agent._run_async_impl(ctx):
            events.append(event)

        assert ctx.session.state["cross_table_fan_out_output"] == {"formulas": []}
        assert len(events) == 1
        assert "No FSLIs to analyse" in events[0].content.parts[0].text

    @pytest.mark.asyncio
    async def test_full_flow_aggregation(self):
        """End-to-end: prepare -> create -> execute -> aggregate with check_type stamping."""
        ctx = MagicMock()
        ctx.session.state = {
            "fsli_extractor_output": {
                "primary_fsli": ["Cash"],
                "sub_fsli": ["Trade receivables"],
            },
            "extracted_tables": {"tables": [{"table_index": 0}]},
            # Simulate sub-agent outputs (FanOutAgent uses "{name}_item_{i}" keys)
            "CrossTableFormulaFanOut_item_0": {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 0, "row_index": 1, "col_index": 1},
                            {"table_index": 1, "row_index": 2, "col_index": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(0,1,1) - cell(1,2,1)"}
                        ],
                    }
                ]
            },
        }

        with patch(
            "google.adk.agents.ParallelAgent.run_async",
            return_value=AsyncIterator(),
        ):
            async for _ in cross_table_fan_out_agent._run_async_impl(ctx):
                pass

        result = ctx.session.state["cross_table_fan_out_output"]
        assert "formulas" in result
        assert len(result["formulas"]) == 1
        assert result["formulas"][0]["check_type"] == "cross_table"


# ===========================================================================
# 7. TestAfterFanOutCallback
# ===========================================================================


class TestAfterFanOutCallback:
    """Test after_fan_out_callback that copies results to reconstructed_formulas."""

    def test_wired_on_fan_out_agent(self):
        """Callback should be registered as after_agent_callback on the FanOutAgent."""
        assert cross_table_fan_out_agent.after_agent_callback is after_fan_out_callback

    def test_copies_formulas_to_reconstructed_formulas(self):
        """Should copy formulas from fan-out output to shared state key."""
        callback_context = MagicMock()
        callback_context.state = {
            "cross_table_fan_out_output": {
                "formulas": [
                    {
                        "check_type": "cross_table",
                        "target_cells": [{"table_index": 0, "row_index": 1, "col_index": 1}],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(0,1,1) - cell(1,2,1)"}],
                    }
                ]
            }
        }

        after_fan_out_callback(callback_context)

        assert len(callback_context.state["reconstructed_formulas"]) == 1
        entry = callback_context.state["reconstructed_formulas"][0]
        assert entry["check_type"] == "cross_table"

    def test_appends_to_existing_reconstructed_formulas(self):
        """Should append, not overwrite, existing entries."""
        existing = {
            "check_type": "in_table",
            "target_cells": [{"table_index": 0, "row_index": 4, "col_index": 1}],
            "actual_value": 100.0,
            "inferred_formulas": [{"formula": "sum_col(0,1,1,3)"}],
        }
        callback_context = MagicMock()
        callback_context.state = {
            "reconstructed_formulas": [existing],
            "cross_table_fan_out_output": {
                "formulas": [
                    {
                        "check_type": "cross_table",
                        "target_cells": [
                            {"table_index": 0, "row_index": 4, "col_index": 1},
                            {"table_index": 1, "row_index": 2, "col_index": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(0,4,1) - cell(1,2,1)"}],
                    }
                ]
            },
        }

        after_fan_out_callback(callback_context)

        assert len(callback_context.state["reconstructed_formulas"]) == 2
        assert callback_context.state["reconstructed_formulas"][0] is existing
        assert callback_context.state["reconstructed_formulas"][1]["check_type"] == "cross_table"

    def test_handles_empty_fan_out_output(self):
        """Should handle empty formulas list gracefully."""
        callback_context = MagicMock()
        callback_context.state = {
            "cross_table_fan_out_output": {"formulas": []},
        }

        after_fan_out_callback(callback_context)

        assert callback_context.state["reconstructed_formulas"] == []

    def test_handles_missing_fan_out_output(self):
        """Should handle missing fan-out output key gracefully."""
        callback_context = MagicMock()
        callback_context.state = {}

        after_fan_out_callback(callback_context)

        assert callback_context.state["reconstructed_formulas"] == []

    def test_handles_pydantic_fan_out_output(self):
        """Should call model_dump() on pydantic fan-out output."""
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {
            "formulas": [
                {
                    "check_type": "cross_table",
                    "target_cells": [{"table_index": 0, "row_index": 1, "col_index": 1}],
                    "actual_value": None,
                    "inferred_formulas": [{"formula": "cell(0,1,1) - cell(1,1,1)"}],
                }
            ]
        }
        callback_context = MagicMock()
        callback_context.state = {"cross_table_fan_out_output": mock_output}

        after_fan_out_callback(callback_context)

        mock_output.model_dump.assert_called_once()
        assert len(callback_context.state["reconstructed_formulas"]) == 1

    def test_multiple_formulas_all_copied(self):
        """Should copy all formulas from output."""
        callback_context = MagicMock()
        callback_context.state = {
            "cross_table_fan_out_output": {
                "formulas": [
                    {"check_type": "cross_table", "inferred_formulas": [{"formula": "f1"}]},
                    {"check_type": "cross_table", "inferred_formulas": [{"formula": "f2"}]},
                    {"check_type": "cross_table", "inferred_formulas": [{"formula": "f3"}]},
                ]
            }
        }

        after_fan_out_callback(callback_context)

        assert len(callback_context.state["reconstructed_formulas"]) == 3
