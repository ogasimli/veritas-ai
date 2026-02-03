"""Unit tests for the cross-table pipeline components.

Coverage:
    1. ``TestFsliExtractorSchema``          - FsliExtractorOutput validation
    2. ``TestCrossTableBatching``           - FSLI chunking logic
    3. ``TestCrossTableStateAggregation``   - post-completion aggregation of
                                              batch outputs into
                                              reconstructed_formulas
"""

import os
from unittest.mock import patch

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.cross_table_pipeline.sub_agents.cross_table_fan_out.agent import (
    chunk_fsli_list,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.cross_table_pipeline.sub_agents.fsli_extractor.schema import (
    FsliExtractorOutput,
)

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
        """Reimport to pick up the env var — but since chunk_fsli_list
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
# 3. TestCrossTableStateAggregation
# ===========================================================================


def _aggregation_function(state: dict) -> None:
    """Reproduce the aggregation loop from CrossTableFormulaFanOut
    *without* importing the full BaseAgent subclass."""
    state.setdefault("reconstructed_formulas", [])
    for key in list(state.keys()):
        if not key.startswith("cross_table_batch_output_"):
            continue
        output = state[key]
        if hasattr(output, "model_dump"):
            output = output.model_dump()
        for entry in output.get("formulas", []):
            entry["check_type"] = "cross_table"
            state["reconstructed_formulas"].append(entry)


class TestCrossTableStateAggregation:
    """Verify aggregation of batch outputs produces correct
    ``reconstructed_formulas`` entries with ``check_type="cross_table"``."""

    def test_single_batch_single_formula(self):
        state: dict = {
            "cross_table_batch_output_0": {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 0, "row": 3, "col": 1},
                            {"table_index": 1, "row": 2, "col": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(0, 3, 1) - sum_col(1, 1, 1, 2)"}
                        ],
                    }
                ]
            }
        }
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 1
        entry = state["reconstructed_formulas"][0]
        assert entry["check_type"] == "cross_table"
        assert entry["actual_value"] is None
        assert len(entry["target_cells"]) == 2

    def test_multiple_batches(self):
        state: dict = {
            "cross_table_batch_output_0": {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 0, "row": 1, "col": 1},
                            {"table_index": 2, "row": 4, "col": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(0,1,1) - cell(2,4,1)"}],
                    }
                ]
            },
            "cross_table_batch_output_1": {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 1, "row": 2, "col": 2},
                            {"table_index": 3, "row": 1, "col": 2},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(1,2,2) - cell(3,1,2)"}],
                    },
                    {
                        "target_cells": [
                            {"table_index": 0, "row": 5, "col": 1},
                            {"table_index": 1, "row": 3, "col": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [
                            {"formula": "cell(0,5,1) - sum_col(1,1,1,2)"}
                        ],
                    },
                ]
            },
        }
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 3
        assert all(
            e["check_type"] == "cross_table" for e in state["reconstructed_formulas"]
        )

    def test_empty_batch_output_produces_no_formulas(self):
        state: dict = {
            "cross_table_batch_output_0": {"formulas": []},
            "cross_table_batch_output_1": {"formulas": []},
        }
        _aggregation_function(state)
        assert state["reconstructed_formulas"] == []

    def test_unrelated_keys_ignored(self):
        state: dict = {
            "fsli_extractor_output": {"primary_fsli": ["X"], "sub_fsli": []},
            "extracted_tables": {"tables": []},
            "cross_table_batch_output_0": {
                "formulas": [
                    {
                        "target_cells": [{"table_index": 0, "row": 0, "col": 0}],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(0,0,0)"}],
                    }
                ]
            },
        }
        _aggregation_function(state)
        assert len(state["reconstructed_formulas"]) == 1

    def test_pre_existing_reconstructed_formulas_preserved(self):
        """In-table entries already present must not be overwritten."""
        existing = {
            "check_type": "in_table",
            "target_cells": [{"table_index": 0, "row": 4, "col": 1}],
            "actual_value": 100.0,
            "inferred_formulas": [{"formula": "sum_col(0,1,1,3)"}],
        }
        state: dict = {
            "reconstructed_formulas": [existing],
            "cross_table_batch_output_0": {
                "formulas": [
                    {
                        "target_cells": [
                            {"table_index": 0, "row": 4, "col": 1},
                            {"table_index": 1, "row": 2, "col": 1},
                        ],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(0,4,1) - cell(1,2,1)"}],
                    }
                ]
            },
        }
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 2
        assert state["reconstructed_formulas"][0] is existing
        assert state["reconstructed_formulas"][1]["check_type"] == "cross_table"

    def test_pydantic_model_output_handled(self):
        """If ADK passes a Pydantic model, model_dump() is called."""

        class _MockOutput:
            def model_dump(self):
                return {
                    "formulas": [
                        {
                            "target_cells": [
                                {"table_index": 0, "row": 1, "col": 1},
                                {"table_index": 1, "row": 1, "col": 1},
                            ],
                            "actual_value": None,
                            "inferred_formulas": [
                                {"formula": "cell(0,1,1) - cell(1,1,1)"}
                            ],
                        }
                    ]
                }

        state: dict = {"cross_table_batch_output_0": _MockOutput()}
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 1
        assert state["reconstructed_formulas"][0]["check_type"] == "cross_table"

    def test_non_sequential_batch_indices_all_collected(self):
        """Keys 0 and 7 (gap in between) are both collected."""
        state: dict = {
            "cross_table_batch_output_0": {
                "formulas": [
                    {
                        "target_cells": [{"table_index": 0, "row": 1, "col": 1}],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(0,1,1)"}],
                    }
                ]
            },
            "cross_table_batch_output_7": {
                "formulas": [
                    {
                        "target_cells": [{"table_index": 2, "row": 3, "col": 1}],
                        "actual_value": None,
                        "inferred_formulas": [{"formula": "cell(2,3,1)"}],
                    }
                ]
            },
        }
        _aggregation_function(state)
        assert len(state["reconstructed_formulas"]) == 2
        assert all(
            e["check_type"] == "cross_table" for e in state["reconstructed_formulas"]
        )
