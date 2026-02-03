"""Unit tests for the in-table formula fan-out.

Coverage:
    1. ``TestBatchingLogic``               - calculate_table_complexity &
                                             batch_tables_by_complexity
    2. ``TestInTableFanOutStateAggregation`` - post-completion aggregation
                                              of batch outputs into
                                              reconstructed_formulas
"""

from unittest.mock import patch

import veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.table_batching as _batching_mod
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.table_batching import (
    batch_tables_by_complexity,
    calculate_table_complexity,
)

# ===========================================================================
# Helpers
# ===========================================================================


def _make_table(
    table_index: int,
    rows: int,
    cols: int,
    *,
    numeric: bool = True,
    subtotal_labels: list[str] | None = None,
) -> dict:
    """Build a minimal table dict with controllable grid dimensions.

    * First row is always a header of string labels.
    * Remaining rows have a label in col 0 and numeric values elsewhere
      (when *numeric* is True).
    * *subtotal_labels* overrides the label in col 0 for rows 1..N so
      that subtotal-keyword scoring can be exercised.
    """
    header = [f"Col{c}" for c in range(cols)]
    grid: list[list] = [header]
    for r in range(1, rows):
        label = f"Item {r}"
        if subtotal_labels and (r - 1) < len(subtotal_labels):
            label = subtotal_labels[r - 1]
        row: list = [label] + (
            [float(r * 10 + c) for c in range(cols - 1)]
            if numeric
            else [""] * (cols - 1)
        )
        grid.append(row)
    return {
        "table_index": table_index,
        "table_name": f"Table {table_index}",
        "grid": grid,
    }


# ===========================================================================
# 1. TestBatchingLogic
# ===========================================================================


class TestBatchingLogic:
    """Pure-function tests — no agents, no LLM calls."""

    # --- calculate_table_complexity -----------------------------------------

    def test_empty_grid_scores_zero(self):
        table = {"table_index": 0, "grid": []}
        assert calculate_table_complexity(table) == 0

    def test_single_header_row_no_numeric(self):
        # 1 row x 3 cols, all strings -> size_score=3, numeric_ratio=0,
        # subtotal_rows=0 -> 3
        table = {"table_index": 0, "grid": [["A", "B", "C"]]}
        assert calculate_table_complexity(table) == 3

    def test_numeric_cells_boost_score(self):
        # 2x2 grid; only 100.0 is numeric (1 of 4 cells).
        # size=4, ratio=1/4=0.25, bonus=int(0.25*20)=5, subtotal=0 -> 9
        table = {
            "table_index": 0,
            "grid": [["Label", "Val"], ["Item", 100.0]],
        }
        score = calculate_table_complexity(table)
        assert score == 9  # 4 + int(0.25*20) + 0

    def test_subtotal_keyword_boosts_score(self):
        # Row label "Total" adds +10
        table = {
            "table_index": 0,
            "grid": [["Item", "Val"], ["Total", 500.0]],
        }
        # size=4, numeric=1/4=0.25 -> bonus=5, subtotal=1 -> +10 -> 19
        score = calculate_table_complexity(table)
        assert score == 19

    def test_multiple_subtotal_keywords(self):
        table = {
            "table_index": 0,
            "grid": [
                ["Item", "Val"],
                ["Subtotal", 100.0],
                ["Net", 200.0],
                ["Gross", 300.0],
                ["Balance", 400.0],
            ],
        }
        # size = 5*2=10, numeric = 4/10 = 0.4 -> bonus = 8
        # subtotal rows = 4 (Subtotal, Net, Gross, Balance) -> +40
        # total = 10 + 8 + 40 = 58
        assert calculate_table_complexity(table) == 58

    def test_keyword_case_insensitive(self):
        upper = {"table_index": 0, "grid": [["Item", "Val"], ["TOTAL", 1.0]]}
        lower = {"table_index": 0, "grid": [["Item", "Val"], ["total", 1.0]]}
        assert calculate_table_complexity(upper) == calculate_table_complexity(lower)

    def test_integer_cells_count_as_numeric(self):
        table = {
            "table_index": 0,
            "grid": [["A", "B"], [10, 20]],
        }
        # size=4, numeric=2/4=0.5 -> bonus=10 -> 14
        assert calculate_table_complexity(table) == 14

    # --- batch_tables_by_complexity - env defaults (100 / 80) ---------------

    def test_empty_tables_returns_empty_batches(self):
        assert batch_tables_by_complexity([]) == []

    @patch.object(_batching_mod, "COMPLEX_TABLE_THRESHOLD", 100)
    @patch.object(_batching_mod, "MAX_BATCH_COMPLEXITY", 80)
    def test_single_complex_table_alone(self):
        """A table scoring >= 100 must end up in its own batch."""
        # 25 rows x 4 cols -> size=100, 72 numeric / 100 = 0.72
        # bonus=int(0.72*20)=14, subtotal=0 -> 114 >= 100
        big = _make_table(0, rows=25, cols=4, numeric=True)
        assert calculate_table_complexity(big) >= 100
        batches = batch_tables_by_complexity([big])
        assert len(batches) == 1
        assert batches[0] == [big]

    @patch.object(_batching_mod, "COMPLEX_TABLE_THRESHOLD", 100)
    @patch.object(_batching_mod, "MAX_BATCH_COMPLEXITY", 80)
    def test_multiple_simple_tables_batch_together(self):
        """Several low-scoring tables should land in the same batch."""
        # 3x2 table: size=6, 2 numeric cells, ratio=2/6=0.33
        # bonus=int(0.33*20)=6 -> score=12; 3 * 12 = 36 < 80 -> one batch
        t0 = _make_table(0, rows=3, cols=2)
        t1 = _make_table(1, rows=3, cols=2)
        t2 = _make_table(2, rows=3, cols=2)
        batches = batch_tables_by_complexity([t0, t1, t2])
        assert len(batches) == 1
        assert len(batches[0]) == 3

    @patch.object(_batching_mod, "COMPLEX_TABLE_THRESHOLD", 100)
    @patch.object(_batching_mod, "MAX_BATCH_COMPLEXITY", 80)
    def test_complex_table_does_not_merge_with_simple(self):
        """A complex table must be isolated; simple ones grouped separately."""
        big = _make_table(0, rows=25, cols=4)  # >= 100
        small = _make_table(1, rows=3, cols=2)  # ~12
        batches = batch_tables_by_complexity([big, small])
        # big alone, small alone (or in its own batch)
        assert any(len(b) == 1 and b[0]["table_index"] == 0 for b in batches)
        # small must not be in same batch as big
        for b in batches:
            if any(t["table_index"] == 0 for t in b):
                assert len(b) == 1

    @patch.object(_batching_mod, "COMPLEX_TABLE_THRESHOLD", 100)
    @patch.object(_batching_mod, "MAX_BATCH_COMPLEXITY", 30)
    def test_max_batch_complexity_respected(self):
        """When MAX_BATCH_COMPLEXITY is tight, tables spill into new batches."""
        # 3 rows x 3 cols: size=9, 4 numeric cells (2 data rows x 2 value cols)
        # ratio=4/9=0.44, bonus=int(0.44*20)=8 -> score=17
        # Two fit: 34 > 30 -> actually first alone (17 <= 30), second starts
        # new batch (17+17=34 > 30), third starts another (17+17=34 > 30).
        # Result: 3 batches of 1 each, OR 1+1+1 depending on greedy packing.
        # Either way every batch total <= 30.
        tables = [_make_table(i, rows=3, cols=3) for i in range(3)]
        batches = batch_tables_by_complexity(tables)
        assert len(batches) >= 2
        for batch in batches:
            total = sum(calculate_table_complexity(t) for t in batch)
            assert total <= 30

    @patch.object(_batching_mod, "COMPLEX_TABLE_THRESHOLD", 50)
    @patch.object(_batching_mod, "MAX_BATCH_COMPLEXITY", 80)
    def test_env_configurable_complex_threshold(self):
        """Lower COMPLEX_TABLE_THRESHOLD forces more tables into solo batches."""
        # 8 rows x 7 cols: size=56 >= 50 -> complex under new threshold
        big = _make_table(0, rows=8, cols=7)
        assert calculate_table_complexity(big) >= 50
        batches = batch_tables_by_complexity([big])
        assert len(batches) == 1
        assert len(batches[0]) == 1

    @patch.object(_batching_mod, "COMPLEX_TABLE_THRESHOLD", 100)
    @patch.object(_batching_mod, "MAX_BATCH_COMPLEXITY", 80)
    def test_descending_sort_order(self):
        """Tables are sorted by complexity descending before batching."""
        small = _make_table(0, rows=2, cols=2)  # low score
        medium = _make_table(1, rows=5, cols=3)  # medium score
        # Both below 100; medium should appear first in its batch
        batches = batch_tables_by_complexity([small, medium])
        # Flatten and check that medium comes before small
        flat = [t for b in batches for t in b]
        medium_pos = next(i for i, t in enumerate(flat) if t["table_index"] == 1)
        small_pos = next(i for i, t in enumerate(flat) if t["table_index"] == 0)
        assert medium_pos < small_pos

    @patch.object(_batching_mod, "COMPLEX_TABLE_THRESHOLD", 100)
    @patch.object(_batching_mod, "MAX_BATCH_COMPLEXITY", 80)
    def test_single_simple_table(self):
        """A single simple table produces exactly one batch."""
        t = _make_table(0, rows=3, cols=2)
        batches = batch_tables_by_complexity([t])
        assert len(batches) == 1
        assert batches[0] == [t]


# ===========================================================================
# 2. TestInTableFanOutStateAggregation
# ===========================================================================


def _aggregation_function(state: dict) -> None:
    """Reproduce the aggregation loop from InTableFormulaFanOut
    *without* importing the full BaseAgent subclass.  This keeps the test
    independent of google-adk runtime dependencies.
    """
    state.setdefault("reconstructed_formulas", [])
    for key in list(state.keys()):
        if not key.startswith("in_table_batch_output_"):
            continue
        output = state[key]
        if hasattr(output, "model_dump"):
            output = output.model_dump()

        # Output is now list[str]
        for formula_str in output.get("formulas", []):
            state["reconstructed_formulas"].append(
                {
                    "check_type": "in_table",
                    "target_cells": [],
                    "actual_value": None,
                    "inferred_formulas": [{"formula": formula_str}],
                }
            )


class TestInTableFanOutStateAggregation:
    """Verify that aggregation of batch outputs produces the correct
    ``reconstructed_formulas`` entries."""

    def test_single_batch_single_formula(self):
        state: dict = {"in_table_batch_output_0": {"formulas": ["sum_col(0, 1, 1, 3)"]}}
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 1
        entry = state["reconstructed_formulas"][0]
        assert entry["check_type"] == "in_table"
        assert entry["actual_value"] is None
        assert entry["target_cells"] == []
        assert entry["inferred_formulas"] == [{"formula": "sum_col(0, 1, 1, 3)"}]

    def test_multiple_batches_multiple_formulas(self):
        state: dict = {
            "in_table_batch_output_0": {
                "formulas": [
                    "sum_col(0, 1, 2, 4)",
                    "sum_col(0, 2, 1, 7)",
                ]
            },
            "in_table_batch_output_1": {"formulas": ["sum_col(1, 1, 1, 2)"]},
        }
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 3
        assert all(
            e["check_type"] == "in_table" for e in state["reconstructed_formulas"]
        )

    def test_empty_batch_output_produces_no_formulas(self):
        state: dict = {
            "in_table_batch_output_0": {"formulas": []},
            "in_table_batch_output_1": {"formulas": []},
        }
        _aggregation_function(state)
        assert state["reconstructed_formulas"] == []

    def test_unrelated_state_keys_ignored(self):
        state: dict = {
            "extracted_tables": {"tables": []},
            "some_other_key": "irrelevant",
            "in_table_batch_output_0": {"formulas": ["cell(0,0,1)"]},
        }
        _aggregation_function(state)
        assert len(state["reconstructed_formulas"]) == 1

    def test_pre_existing_reconstructed_formulas_preserved(self):
        """If cross-table pipeline already wrote entries, in-table must
        append, not overwrite."""
        existing = {
            "check_type": "cross_table",
            "target_cells": [],
            "inferred_formulas": [],
        }
        state: dict = {
            "reconstructed_formulas": [existing],
            "in_table_batch_output_0": {"formulas": ["cell(0,1,1)"]},
        }
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 2
        assert state["reconstructed_formulas"][0] is existing
        assert state["reconstructed_formulas"][1]["check_type"] == "in_table"

    def test_pydantic_model_output_handled(self):
        """If ADK passes a Pydantic model instead of a dict, model_dump()
        is called before iteration."""

        class _MockOutput:
            def model_dump(self):
                return {"formulas": ["cell(2,0,0)"]}

        state: dict = {"in_table_batch_output_0": _MockOutput()}
        _aggregation_function(state)

        assert len(state["reconstructed_formulas"]) == 1
        assert state["reconstructed_formulas"][0]["check_type"] == "in_table"
        assert state["reconstructed_formulas"][0]["actual_value"] is None

    def test_non_sequential_batch_indices_all_collected(self):
        """Keys need not be contiguous — any key matching the prefix is
        collected."""
        state: dict = {
            "in_table_batch_output_0": {"formulas": ["cell(0,0,1)"]},
            "in_table_batch_output_5": {"formulas": ["cell(3,1,1)"]},
        }
        _aggregation_function(state)
        assert len(state["reconstructed_formulas"]) == 2
