"""Unit tests for the Aggregator agent callbacks.

No LLM calls are made.  The tests exercise:
    1. ``TestExtractFormulaString``   - helper that normalises the various
                                        shapes a formula can arrive in
    2. ``TestEvaluateInTable``        - per-entry evaluation when
                                        ``actual_value`` is (or is not) set
    3. ``TestEvaluateCrossTable``     - evaluation of difference formulas
    4. ``TestBeforeAgentCallback``    - full async entry-point: state read,
                                        dispatch, sort, write
    5. ``TestAggregatorSchema``       - Pydantic round-trip validation of
                                        NumericIssue / AggregatorOutput
"""

from unittest.mock import MagicMock

import pytest

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.aggregator.callbacks import (
    _evaluate_cross_table,
    _evaluate_in_table,
    _extract_formula_string,
    before_agent_callback,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.aggregator.schema import (
    AggregatorOutput,
    NumericIssue,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------
# Two-table scenario used across most tests.
#
#   Table 0 - "Balance Sheet"
#     Row 0: ["Item",              "2024",  "2023"]   ← headers
#     Row 1: ["Current Assets",    "",      ""]       ← section label
#     Row 2: ["Cash",              500.0,   400.0]
#     Row 3: ["Receivables",       300.0,   250.0]
#     Row 4: ["Total Current",     800.0,   650.0]    ← == sum(rows 2-3)
#     Row 5: ["Non-Current",       1200.0,  1100.0]
#     Row 6: ["TOTAL ASSETS",      2000.0,  1750.0]   ← == 800 + 1200
#
#   Table 1 - "Note 5 - Cash"
#     Row 0: ["Component",  "Amount"]
#     Row 1: ["Bank A",     300.0]
#     Row 2: ["Bank B",     200.0]
#     Row 3: ["Total",      500.0]   ← == Table-0 Cash (500)
#
# All cross-table relationships HOLD in this data set.  Tests that need a
# discrepancy deep-copy and swap the relevant cell.

TABLES_ENVELOPE: dict = {
    "tables": [
        {
            "table_index": 0,
            "table_name": "Balance Sheet",
            "grid": [
                ["Item", "2024", "2023"],
                ["Current Assets", "", ""],
                ["Cash", 500.0, 400.0],
                ["Receivables", 300.0, 250.0],
                ["Total Current", 800.0, 650.0],
                ["Non-Current", 1200.0, 1100.0],
                ["TOTAL ASSETS", 2000.0, 1750.0],
            ],
        },
        {
            "table_index": 1,
            "table_name": "Note 5 - Cash",
            "grid": [
                ["Component", "Amount"],
                ["Bank A", 300.0],
                ["Bank B", 200.0],
                ["Total", 500.0],
            ],
        },
    ]
}

# Pre-built lookup maps matching what the callback constructs internally.
_TABLE_GRIDS: dict[int, list] = {
    t["table_index"]: t["grid"] for t in TABLES_ENVELOPE["tables"]
}
_TABLE_NAMES: dict[int, str] = {
    t["table_index"]: t["table_name"] for t in TABLES_ENVELOPE["tables"]
}


def _mock_ctx(state: dict) -> MagicMock:
    """Return a mock CallbackContext backed by a real dict."""
    ctx = MagicMock()
    ctx.state = state
    return ctx


def _with_note_total(value: float) -> dict:
    """Return a fresh TABLES_ENVELOPE with Note-5 Total overridden."""
    note = {
        **TABLES_ENVELOPE["tables"][1],
        "grid": [
            ["Component", "Amount"],
            ["Bank A", 300.0],
            ["Bank B", 200.0],
            ["Total", value],
        ],
    }
    return {"tables": [TABLES_ENVELOPE["tables"][0], note]}


# ===========================================================================
# 1. _extract_formula_string
# ===========================================================================


class TestExtractFormulaString:
    """Isolated tests for the shape-normalisation helper."""

    # --- happy paths --------------------------------------------------------

    def test_dict_with_formula_key(self):
        assert _extract_formula_string({"formula": "cell(0,1,1)"}) == "cell(0,1,1)"

    def test_bare_string(self):
        assert _extract_formula_string("sum_col(0,1,2,3)") == "sum_col(0,1,2,3)"

    def test_pydantic_like_object(self):
        class _Obj:
            formula = "cell(1,2,3)"

        assert _extract_formula_string(_Obj()) == "cell(1,2,3)"

    # --- None / empty / wrong types -----------------------------------------

    def test_none_returns_none(self):
        assert _extract_formula_string(None) is None

    def test_integer_returns_none(self):
        assert _extract_formula_string(42) is None

    def test_list_returns_none(self):
        assert _extract_formula_string(["cell(0,0,0)"]) is None

    def test_empty_dict_returns_none(self):
        assert _extract_formula_string({}) is None

    def test_dict_formula_value_is_nested_dict(self):
        """LLM occasionally nests a dict under 'formula' - must not crash."""
        assert _extract_formula_string({"formula": {"nested": True}}) is None

    def test_dict_formula_value_is_none(self):
        assert _extract_formula_string({"formula": None}) is None

    def test_dict_formula_value_is_integer(self):
        assert _extract_formula_string({"formula": 42}) is None

    def test_empty_string_is_returned(self):
        """Empty string IS a valid str; the engine will evaluate it to 0.0."""
        assert _extract_formula_string({"formula": ""}) == ""

    def test_object_without_formula_attribute(self):
        class _NoAttr:
            pass

        assert _extract_formula_string(_NoAttr()) is None


# ===========================================================================
# 2. _evaluate_in_table
# ===========================================================================


class TestEvaluateInTable:
    """Pure-function tests - no agents, no async."""

    # --- actual_value is None (current pipeline shape) ---------------------

    def test_none_actual_value_returns_empty(self):
        """The in-table fan-out sets actual_value=None; must be a no-op."""
        entry = {
            "check_type": "in_table",
            "actual_value": None,
            "table_index": 0,
            "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
        }
        assert _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_missing_actual_value_key_returns_empty(self):
        entry = {
            "check_type": "in_table",
            "table_index": 0,
            "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
        }
        assert _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    # --- discrepancy detected -----------------------------------------------

    def test_detects_discrepancy(self):
        """sum_col(0, 1, 2, 3) = Cash(500) + Recv(300) = 800.
        actual = 750  →  difference = 50."""
        entry = {
            "check_type": "in_table",
            "actual_value": 750.0,
            "table_index": 0,
            "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
        }
        issues = _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES)

        assert len(issues) == 1
        assert issues[0]["check_type"] == "in_table"
        assert issues[0]["table_name"] == "Balance Sheet"
        assert issues[0]["table_index"] == 0
        assert issues[0]["formula"] == "sum_col(0, 1, 2, 3)"
        assert issues[0]["calculated_value"] == 800.0
        assert issues[0]["actual_value"] == 750.0
        assert issues[0]["difference"] == 50.0

    def test_negative_difference_preserved(self):
        """calculated < actual  →  difference is negative."""
        entry = {
            "check_type": "in_table",
            "actual_value": 900.0,
            "table_index": 0,
            "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
        }
        issues = _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["difference"] == -100.0

    # --- threshold boundary -------------------------------------------------

    def test_difference_below_threshold_suppressed(self):
        """abs(diff) = 0.5 < 1.0  →  no issue."""
        entry = {
            "check_type": "in_table",
            "actual_value": 800.5,
            "table_index": 0,
            "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
        }
        assert _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_difference_exactly_at_threshold_is_flagged(self):
        """abs(diff) == 1.0  →  flagged (>= not >)."""
        entry = {
            "check_type": "in_table",
            "actual_value": 799.0,  # 800 - 799 = 1.0
            "table_index": 0,
            "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
        }
        issues = _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["difference"] == 1.0

    def test_exact_match_produces_no_issue(self):
        entry = {
            "check_type": "in_table",
            "actual_value": 800.0,
            "table_index": 0,
            "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
        }
        assert _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    # --- multiple inferred_formulas -----------------------------------------

    def test_only_exceeding_formulas_reported(self):
        """First formula matches (800 == 800); second sums rows 2-5 = 2800."""
        entry = {
            "check_type": "in_table",
            "actual_value": 800.0,
            "table_index": 0,
            "inferred_formulas": [
                {"formula": "sum_col(0, 1, 2, 3)"},  # 800 - exact match
                {"formula": "sum_col(0, 1, 2, 5)"},  # 500+300+800+1200 = 2800
            ],
        }
        issues = _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["calculated_value"] == 2800.0
        assert issues[0]["difference"] == 2000.0

    def test_all_formulas_match_produces_nothing(self):
        """Both formulas evaluate to 500 == actual."""
        entry = {
            "check_type": "in_table",
            "actual_value": 500.0,
            "table_index": 0,
            "inferred_formulas": [
                {"formula": "cell(0, 2, 1)"},  # Cash 2024 = 500
                {"formula": "sum_col(1, 1, 1, 2)"},  # Note: 300 + 200 = 500
            ],
        }
        assert _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    # --- edge cases ---------------------------------------------------------

    def test_empty_inferred_formulas_list(self):
        entry = {
            "check_type": "in_table",
            "actual_value": 100.0,
            "table_index": 0,
            "inferred_formulas": [],
        }
        assert _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_missing_inferred_formulas_key(self):
        entry = {"check_type": "in_table", "actual_value": 100.0, "table_index": 0}
        assert _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_bad_formula_engine_returns_zero(self):
        """Unparsable formula → engine returns 0.0; compared to actual=100 → diff=-100."""
        entry = {
            "check_type": "in_table",
            "actual_value": 100.0,
            "table_index": 0,
            "inferred_formulas": [{"formula": "not_a_function(0,0)"}],
        }
        issues = _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["calculated_value"] == 0.0
        assert issues[0]["difference"] == -100.0

    def test_unparsable_item_in_list_is_skipped(self):
        """None in the list is silently skipped; the valid entry is evaluated."""
        entry = {
            "check_type": "in_table",
            "actual_value": 100.0,
            "table_index": 0,
            "inferred_formulas": [None, {"formula": "cell(0, 2, 1)"}],
            # None  →  _extract returns None  →  continue
            # cell  →  500 vs 100  →  diff = 400
        }
        issues = _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["calculated_value"] == 500.0

    def test_missing_table_index_falls_back_in_name(self):
        """table_index absent in entry → .get returns None → name = 'Table None'."""
        entry = {
            "check_type": "in_table",
            "actual_value": 0.0,
            "inferred_formulas": [{"formula": "cell(0, 2, 1)"}],  # 500 vs 0
        }
        issues = _evaluate_in_table(entry, _TABLE_GRIDS, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["table_name"] == "Table None"
        assert issues[0]["table_index"] is None


# ===========================================================================
# 3. _evaluate_cross_table
# ===========================================================================


class TestEvaluateCrossTable:
    """Pure-function tests for cross-table difference formulas."""

    # --- relationship holds (diff == 0) ------------------------------------

    def test_matching_pair_no_issue(self):
        """BS Cash (500) - Note Total (500) = 0."""
        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
        }
        assert _evaluate_cross_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_subtotal_vs_components_holds(self):
        """Total Current (800) - sum(Cash, Recv) = 800 - 800 = 0."""
        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [
                {"formula": "cell(0, 4, 1) - sum_cells((0,2,1), (0,3,1))"}
            ],
        }
        assert _evaluate_cross_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    # --- discrepancy detected -----------------------------------------------

    def test_detects_positive_discrepancy(self):
        """Note Total set to 350  →  500 - 350 = 150."""
        grids = {0: _TABLE_GRIDS[0], 1: [row[:] for row in _TABLE_GRIDS[1]]}
        grids[1][3][1] = 350.0

        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
        }
        issues = _evaluate_cross_table(entry, grids, _TABLE_NAMES)

        assert len(issues) == 1
        assert issues[0]["check_type"] == "cross_table"
        assert issues[0]["formula"] == "cell(0, 2, 1) - cell(1, 3, 1)"
        assert issues[0]["calculated_value"] == 150.0
        assert issues[0]["actual_value"] == 0.0
        assert issues[0]["difference"] == 150.0

    def test_detects_negative_discrepancy(self):
        """Note Total set to 700  →  500 - 700 = -200."""
        grids = {0: _TABLE_GRIDS[0], 1: [row[:] for row in _TABLE_GRIDS[1]]}
        grids[1][3][1] = 700.0

        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
        }
        issues = _evaluate_cross_table(entry, grids, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["difference"] == -200.0

    # --- threshold boundary -------------------------------------------------

    def test_difference_below_threshold_suppressed(self):
        """Note Total = 499.5  →  diff = 0.5 < 1.0."""
        grids = {0: _TABLE_GRIDS[0], 1: [row[:] for row in _TABLE_GRIDS[1]]}
        grids[1][3][1] = 499.5

        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
        }
        assert _evaluate_cross_table(entry, grids, _TABLE_NAMES) == []

    def test_difference_exactly_at_threshold_is_flagged(self):
        """Note Total = 499  →  diff = 1.0."""
        grids = {0: _TABLE_GRIDS[0], 1: [row[:] for row in _TABLE_GRIDS[1]]}
        grids[1][3][1] = 499.0

        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
        }
        issues = _evaluate_cross_table(entry, grids, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["difference"] == 1.0

    # --- multiple inferred_formulas -----------------------------------------

    def test_only_failing_formulas_reported(self):
        """First formula holds (sum matches cell); second has diff = 150."""
        grids = {0: _TABLE_GRIDS[0], 1: [row[:] for row in _TABLE_GRIDS[1]]}
        grids[1][3][1] = 350.0  # Note Total → 350

        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [
                # sum_col(1,1,1,2) = Bank A(300) + Bank B(200) = 500; Cash = 500 → 0
                {"formula": "cell(0, 2, 1) - sum_col(1, 1, 1, 2)"},
                # cell(1,3,1) = 350; Cash = 500 → 150
                {"formula": "cell(0, 2, 1) - cell(1, 3, 1)"},
            ],
        }
        issues = _evaluate_cross_table(entry, grids, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["difference"] == 150.0

    def test_both_formulas_failing(self):
        """Two formulas, both producing issues with different magnitudes."""
        grids = {0: _TABLE_GRIDS[0], 1: [row[:] for row in _TABLE_GRIDS[1]]}
        grids[1][3][1] = 350.0  # Note Total → 350

        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [
                # Cash(500) - Note Total(350) = 150
                {"formula": "cell(0, 2, 1) - cell(1, 3, 1)"},
                # Receivables(300) - Note Total(350) = -50
                {"formula": "cell(0, 3, 1) - cell(1, 3, 1)"},
            ],
        }
        issues = _evaluate_cross_table(entry, grids, _TABLE_NAMES)
        assert len(issues) == 2
        diffs = {i["difference"] for i in issues}
        assert diffs == {150.0, -50.0}

    # --- edge cases ---------------------------------------------------------

    def test_empty_inferred_formulas_list(self):
        entry = {"check_type": "cross_table", "inferred_formulas": []}
        assert _evaluate_cross_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_missing_inferred_formulas_key(self):
        entry = {"check_type": "cross_table"}
        assert _evaluate_cross_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_bad_formula_evaluates_to_zero_below_threshold(self):
        """Unparsable formula → 0.0, which is below threshold."""
        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [{"formula": "garbage!!!"}],
        }
        assert _evaluate_cross_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_unparsable_item_in_list_is_skipped(self):
        """None in the list does not crash; valid formula (= 0) produces no issue."""
        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [None, {"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
        }
        assert _evaluate_cross_table(entry, _TABLE_GRIDS, _TABLE_NAMES) == []

    def test_reference_to_missing_table_evaluates_to_zero(self):
        """cell(99,…) → 0.0 per formula_engine; Cash(500) - 0 = 500."""
        entry = {
            "check_type": "cross_table",
            "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(99, 0, 0)"}],
        }
        issues = _evaluate_cross_table(entry, _TABLE_GRIDS, _TABLE_NAMES)
        assert len(issues) == 1
        assert issues[0]["difference"] == 500.0


# ===========================================================================
# 4. before_agent_callback  (async, end-to-end)
# ===========================================================================


class TestBeforeAgentCallback:
    """Full callback: reads state, dispatches, sorts, writes."""

    # --- empty / missing state keys ----------------------------------------

    @pytest.mark.asyncio
    async def test_completely_empty_state(self):
        state: dict = {}
        await before_agent_callback(_mock_ctx(state))
        assert state["formula_execution_issues"] == []

    @pytest.mark.asyncio
    async def test_empty_reconstructed_formulas_list(self):
        state: dict = {
            "reconstructed_formulas": [],
            "extracted_tables": TABLES_ENVELOPE,
        }
        await before_agent_callback(_mock_ctx(state))
        assert state["formula_execution_issues"] == []

    @pytest.mark.asyncio
    async def test_missing_extracted_tables_all_cells_zero(self):
        """Without grids every cell reference evaluates to 0.0.
        A difference formula like ``cell(a) - cell(b)`` → 0 - 0 = 0
        → below threshold → no issues."""
        state: dict = {
            "reconstructed_formulas": [
                {
                    "check_type": "cross_table",
                    "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
                }
            ],
        }
        await before_agent_callback(_mock_ctx(state))
        assert state["formula_execution_issues"] == []

    # --- single cross-table issue ------------------------------------------

    @pytest.mark.asyncio
    async def test_single_cross_table_issue_detected(self):
        """Note Total = 350 → diff = 150."""
        state: dict = {
            "reconstructed_formulas": [
                {
                    "check_type": "cross_table",
                    "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
                }
            ],
            "extracted_tables": _with_note_total(350.0),
        }
        await before_agent_callback(_mock_ctx(state))

        issues = state["formula_execution_issues"]
        assert len(issues) == 1
        assert issues[0]["check_type"] == "cross_table"
        assert issues[0]["difference"] == 150.0

    # --- single in-table issue (actual_value populated) -------------------

    @pytest.mark.asyncio
    async def test_single_in_table_issue_detected(self):
        """sum = 800, actual = 750 → diff = 50."""
        state: dict = {
            "reconstructed_formulas": [
                {
                    "check_type": "in_table",
                    "table_index": 0,
                    "actual_value": 750.0,
                    "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
                }
            ],
            "extracted_tables": TABLES_ENVELOPE,
        }
        await before_agent_callback(_mock_ctx(state))

        issues = state["formula_execution_issues"]
        assert len(issues) == 1
        assert issues[0]["check_type"] == "in_table"
        assert issues[0]["table_name"] == "Balance Sheet"
        assert issues[0]["difference"] == 50.0

    # --- in-table with actual_value=None is silently skipped ---------------

    @pytest.mark.asyncio
    async def test_in_table_none_actual_value_produces_nothing(self):
        """Pipeline-current shape; must not produce an issue."""
        state: dict = {
            "reconstructed_formulas": [
                {
                    "check_type": "in_table",
                    "actual_value": None,
                    "table_index": 0,
                    "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
                }
            ],
            "extracted_tables": TABLES_ENVELOPE,
        }
        await before_agent_callback(_mock_ctx(state))
        assert state["formula_execution_issues"] == []

    # --- sort order: absolute difference descending ------------------------

    @pytest.mark.asyncio
    async def test_issues_sorted_by_absolute_difference(self):
        """Three issues produced; verify descending |diff| order.

        Note Total = 700 so that:
            cross-table A:  Cash(500) - NoteTotal(700)       = -200
            cross-table B:  TotalCurrent(800) - NoteTotal(700) =  100
            in-table:       sum(rows 2-3) = 800 vs actual 750  =   50
        Sorted: |200| > |100| > |50|
        """
        state: dict = {
            "reconstructed_formulas": [
                # Intentionally listed in NON-sorted order
                {
                    "check_type": "in_table",
                    "table_index": 0,
                    "actual_value": 750.0,
                    "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
                },
                {
                    "check_type": "cross_table",
                    "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
                },
                {
                    "check_type": "cross_table",
                    "inferred_formulas": [{"formula": "cell(0, 4, 1) - cell(1, 3, 1)"}],
                },
            ],
            "extracted_tables": _with_note_total(700.0),
        }
        await before_agent_callback(_mock_ctx(state))

        issues = state["formula_execution_issues"]
        assert len(issues) == 3

        abs_diffs = [abs(i["difference"]) for i in issues]
        assert abs_diffs == sorted(abs_diffs, reverse=True)

        assert issues[0]["difference"] == -200.0  # |200|
        assert issues[1]["difference"] == 100.0  # |100|
        assert issues[2]["difference"] == 50.0  # |50|

    # --- unknown check_type is silently skipped ----------------------------

    @pytest.mark.asyncio
    async def test_unknown_check_type_skipped(self):
        state: dict = {
            "reconstructed_formulas": [
                {
                    "check_type": "legacy_check",
                    "inferred_formulas": [{"formula": "cell(0,2,1)"}],
                }
            ],
            "extracted_tables": TABLES_ENVELOPE,
        }
        await before_agent_callback(_mock_ctx(state))
        assert state["formula_execution_issues"] == []

    # --- mixed pipeline: in-table skipped + cross-table flagged ------------

    @pytest.mark.asyncio
    async def test_mixed_none_actual_and_cross_table(self):
        """in-table entry (actual=None) produces nothing; cross-table does."""
        state: dict = {
            "reconstructed_formulas": [
                {
                    "check_type": "in_table",
                    "actual_value": None,
                    "table_index": 0,
                    "inferred_formulas": [{"formula": "sum_col(0, 1, 2, 3)"}],
                },
                {
                    "check_type": "cross_table",
                    "inferred_formulas": [{"formula": "cell(0, 2, 1) - cell(1, 3, 1)"}],
                },
            ],
            "extracted_tables": _with_note_total(200.0),  # diff = 300
        }
        await before_agent_callback(_mock_ctx(state))

        issues = state["formula_execution_issues"]
        assert len(issues) == 1
        assert issues[0]["check_type"] == "cross_table"
        assert issues[0]["difference"] == 300.0

    # --- multiple formulas in a single entry --------------------------------

    @pytest.mark.asyncio
    async def test_two_formulas_in_one_cross_table_entry(self):
        """Both formulas in the same entry produce separate issues."""
        state: dict = {
            "reconstructed_formulas": [
                {
                    "check_type": "cross_table",
                    "inferred_formulas": [
                        # Cash(500) - NoteTotal(350) = 150
                        {"formula": "cell(0, 2, 1) - cell(1, 3, 1)"},
                        # Recv(300) - NoteTotal(350) = -50
                        {"formula": "cell(0, 3, 1) - cell(1, 3, 1)"},
                    ],
                }
            ],
            "extracted_tables": _with_note_total(350.0),
        }
        await before_agent_callback(_mock_ctx(state))

        issues = state["formula_execution_issues"]
        assert len(issues) == 2
        # Sorted: |150| > |50|
        assert issues[0]["difference"] == 150.0
        assert issues[1]["difference"] == -50.0


# ===========================================================================
# 5. AggregatorOutput / NumericIssue schema
# ===========================================================================


class TestAggregatorSchema:
    """Pydantic validation round-trips."""

    def test_valid_single_issue(self):
        out = AggregatorOutput(
            issues=[
                NumericIssue(
                    issue_description="Cash mismatch of 150 between BS and Note.",
                    check_type="cross_table",
                    formula="cell(0, 2, 1) - cell(1, 3, 1)",
                    difference=150.0,
                )
            ]
        )
        assert len(out.issues) == 1
        assert out.issues[0].difference == 150.0
        assert out.error is None

    def test_empty_issues_list_is_valid(self):
        out = AggregatorOutput(issues=[])
        assert out.issues == []

    def test_defaults_produce_empty_issues(self):
        out = AggregatorOutput()
        assert out.issues == []

    def test_model_dump_round_trip(self):
        original = AggregatorOutput(
            issues=[
                NumericIssue(
                    issue_description="In-table off by 50.",
                    check_type="in_table",
                    formula="sum_col(0, 1, 2, 3)",
                    difference=50.0,
                ),
                NumericIssue(
                    issue_description="Cross-table off by -200.",
                    check_type="cross_table",
                    formula="cell(0,2,1) - cell(1,3,1)",
                    difference=-200.0,
                ),
            ]
        )
        dumped = original.model_dump()
        restored = AggregatorOutput.model_validate(dumped)
        assert restored == original

    def test_error_field_inherited_from_base(self):
        """BaseAgentOutput.error is settable on AggregatorOutput."""
        from veritas_ai_agent.schemas import AgentError

        err = AgentError(
            agent_name="Aggregator",
            error_type="rate_limit",
            error_message="429 - back off",
        )
        out = AggregatorOutput(error=err)
        assert out.error is not None
        assert out.error.agent_name == "Aggregator"
        assert out.issues == []  # default
