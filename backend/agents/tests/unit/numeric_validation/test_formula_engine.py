"""Unit tests for the multi-table formula engine (evaluate_formula_with_tables).

Grids arrive pre-parsed (floats + label strings); no string parsing happens
inside the engine.
"""

from typing import ClassVar

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.formula_engine import (
    evaluate_formula_with_tables,
)


class TestNewFormulaEngine:
    # Shared fixture: a realistic two-table document
    #   Table 0: Balance Sheet
    #   Table 1: Note 5 - Cash breakdown
    GRIDS: ClassVar[dict] = {
        0: [
            ["Item", "2024", "2023"],
            ["Current Assets", "", ""],
            ["Cash", 500.0, 400.0],
            ["Receivables", 300.0, 250.0],
            ["Total Current", 800.0, 650.0],
            ["Non-Current", 1200.0, 1100.0],
            ["TOTAL ASSETS", 2000.0, 1750.0],
        ],
        1: [
            ["Cash component", "Amount"],
            ["Bank A", 300.0],
            ["Bank B", 200.0],
            ["Total Cash", 500.0],
        ],
    }

    # --- cell() ------------------------------------------------------------
    def test_cell_numeric(self):
        assert evaluate_formula_with_tables("cell(0, 2, 1)", self.GRIDS) == 500.0

    def test_cell_label_returns_zero(self):
        # "Item" is a string label → 0.0
        assert evaluate_formula_with_tables("cell(0, 0, 0)", self.GRIDS) == 0.0

    def test_cell_empty_string_returns_zero(self):
        # "Current Assets" row, col 1 is ""
        assert evaluate_formula_with_tables("cell(0, 1, 1)", self.GRIDS) == 0.0

    def test_cell_different_table(self):
        assert evaluate_formula_with_tables("cell(1, 1, 1)", self.GRIDS) == 300.0

    # --- sum_col() ---------------------------------------------------------
    def test_sum_col_current_assets(self):
        # Cash (row2) + Receivables (row3) col 1  →  500 + 300 = 800
        assert evaluate_formula_with_tables("sum_col(0, 1, 2, 3)", self.GRIDS) == 800.0

    def test_sum_col_all_2023(self):
        # rows 2-5, col 2  →  400 + 250 + 650 + 1100 = 2400
        assert evaluate_formula_with_tables("sum_col(0, 2, 2, 5)", self.GRIDS) == 2400.0

    def test_sum_col_note_detail(self):
        # Note table rows 1-2, col 1  →  300 + 200 = 500
        assert evaluate_formula_with_tables("sum_col(1, 1, 1, 2)", self.GRIDS) == 500.0

    def test_sum_col_includes_label_rows_as_zero(self):
        # rows 0-2 col 1 in table 0: "" (header) + "" (section) + 500 = 500
        assert evaluate_formula_with_tables("sum_col(0, 1, 0, 2)", self.GRIDS) == 500.0

    # --- sum_row() ---------------------------------------------------------
    def test_sum_row_cash_both_years(self):
        # row 2, cols 1-2  →  500 + 400 = 900
        assert evaluate_formula_with_tables("sum_row(0, 2, 1, 2)", self.GRIDS) == 900.0

    def test_sum_row_single_col(self):
        assert evaluate_formula_with_tables("sum_row(0, 2, 1, 1)", self.GRIDS) == 500.0

    # --- sum_cells() (non-contiguous, cross-table) -------------------------
    def test_sum_cells_same_table(self):
        # Cash 2024 + Receivables 2024  →  500 + 300 = 800
        assert (
            evaluate_formula_with_tables("sum_cells((0,2,1), (0,3,1))", self.GRIDS)
            == 800.0
        )

    def test_sum_cells_cross_table(self):
        # BS Cash 2024 (500) + Note Bank B (200)  →  700
        assert (
            evaluate_formula_with_tables("sum_cells((0,2,1), (1,2,1))", self.GRIDS)
            == 700.0
        )

    def test_sum_cells_single_coord(self):
        assert evaluate_formula_with_tables("sum_cells((1,3,1))", self.GRIDS) == 500.0

    # --- arithmetic across tables ------------------------------------------
    def test_cross_table_equality_check(self):
        # BS Cash 2024 (500) - Note Total Cash (500)  →  0
        assert (
            evaluate_formula_with_tables("cell(0, 2, 1) - cell(1, 3, 1)", self.GRIDS)
            == 0.0
        )

    def test_subtotal_vs_items(self):
        # Total Current (800) - (Cash + Receivables) = 0
        assert (
            evaluate_formula_with_tables(
                "cell(0, 4, 1) - sum_cells((0,2,1), (0,3,1))", self.GRIDS
            )
            == 0.0
        )

    def test_grand_total_vs_subtotals(self):
        # TOTAL ASSETS (2000) - (Total Current (800) + Non-Current (1200)) = 0
        assert (
            evaluate_formula_with_tables(
                "cell(0, 6, 1) - (cell(0, 4, 1) + cell(0, 5, 1))", self.GRIDS
            )
            == 0.0
        )

    # --- allowed builtins --------------------------------------------------
    def test_abs(self):
        grids = {0: [[-250.0, 100.0]]}
        assert evaluate_formula_with_tables("abs(cell(0, 0, 0))", grids) == 250.0

    def test_round_division(self):
        grids = {0: [[100.0, 3.0]]}
        assert (
            evaluate_formula_with_tables("round(cell(0,0,0) / cell(0,0,1))", grids)
            == 33.0
        )

    def test_min_max(self):
        grids = {0: [[10.0, 50.0, 30.0]]}
        assert (
            evaluate_formula_with_tables(
                "min(cell(0,0,0), cell(0,0,1), cell(0,0,2))", grids
            )
            == 10.0
        )
        assert (
            evaluate_formula_with_tables(
                "max(cell(0,0,0), cell(0,0,1), cell(0,0,2))", grids
            )
            == 50.0
        )

    # --- integer cells (not just float) ------------------------------------
    def test_integer_cells(self):
        grids = {0: [[100, 200]]}
        assert evaluate_formula_with_tables("cell(0,0,0) + cell(0,0,1)", grids) == 300.0

    # --- out-of-bounds / missing table -------------------------------------
    def test_missing_table_index_returns_zero(self):
        grids = {0: [[100.0]]}
        assert evaluate_formula_with_tables("cell(99, 0, 0)", grids) == 0.0

    def test_out_of_bounds_row_returns_zero(self):
        grids = {0: [[100.0]]}
        assert evaluate_formula_with_tables("cell(0, 99, 0)", grids) == 0.0

    def test_out_of_bounds_col_returns_zero(self):
        grids = {0: [[100.0]]}
        assert evaluate_formula_with_tables("cell(0, 0, 99)", grids) == 0.0

    # --- error handling ----------------------------------------------------
    def test_invalid_function_name_returns_zero(self):
        grids = {0: [[100.0]]}
        assert evaluate_formula_with_tables("unknown_fn(0,0,0)", grids) == 0.0

    def test_syntax_error_returns_zero(self):
        grids = {0: [[100.0]]}
        assert evaluate_formula_with_tables("cell(0,0,0) +", grids) == 0.0

    def test_empty_formula_returns_zero(self):
        grids = {0: [[100.0]]}
        assert evaluate_formula_with_tables("", grids) == 0.0

    def test_empty_grids_dict(self):
        assert evaluate_formula_with_tables("cell(0,0,0)", {}) == 0.0

    # --- security: no access to builtins -----------------------------------
    def test_cannot_access_builtins(self):
        grids = {0: [[1.0]]}
        # __import__ is not in the namespace
        assert evaluate_formula_with_tables("__import__('os')", grids) == 0.0

    def test_cannot_access_globals(self):
        grids = {0: [[1.0]]}
        assert evaluate_formula_with_tables("globals()", grids) == 0.0

    # --- None cells --------------------------------------------------------
    def test_none_cell_returns_zero(self):
        grids = {0: [[None, 100.0]]}
        assert evaluate_formula_with_tables("cell(0,0,0) + cell(0,0,1)", grids) == 100.0

    # --- sum over range that includes labels and numbers -------------------
    def test_sum_col_mixed_labels_and_numbers(self):
        grids = {
            0: [
                ["Header", "2024"],
                ["Section", ""],  # label row, col 1 = ""
                ["Item A", 100.0],
                ["Item B", 200.0],
                ["Total", 300.0],  # this is what we'd check against
            ]
        }
        # Sum rows 1-3 col 1  →  0 + 100 + 200 = 300
        assert evaluate_formula_with_tables("sum_col(0, 1, 1, 3)", grids) == 300.0
