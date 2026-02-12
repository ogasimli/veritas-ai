"""Unit tests for formula_replicator.py

Tests cover:
- Vertical replication (sum_col, sum_cells)
- Horizontal replication (sum_row, sum_cells)
- Compound arithmetic replication (cell() +/- cell())
- Direction detection for compound formulas
- Edge cases: empty target cells, non-numeric source cells, etc.
"""

from typing import ClassVar

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.formula_replicator import (
    replicate_formulas,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.schema import (
    TargetCell,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.logic_reconciliation_check.sub_agents.fan_out.schema import (
    LogicInferredFormula,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.schema import (
    HorizontalVerticalCheckInferredFormula,
)


class TestVerticalReplication:
    """Test vertical (column-based) formula replication."""

    def test_sum_col_basic(self):
        """Replicate sum_col formula to other numeric columns."""
        # Simple table with numeric columns 1-3
        grid = [
            ["Item", "2024", "2023", "2022"],
            ["Revenue", 100, 95, 90],
            ["Cost", 40, 38, 36],
            ["Profit", 60, 57, 54],  # Row 3 is sum of rows 1-2
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula="sum_col(0, 1, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        # Should get formulas for columns 1, 2, 3
        assert len(result) == 3
        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[1] == "sum_col(0, 1, 1, 2)"  # Original
        assert formulas_by_col[2] == "sum_col(0, 2, 1, 2)"  # Replicated to col 2
        assert formulas_by_col[3] == "sum_col(0, 3, 1, 2)"  # Replicated to col 3

    def test_sum_col_empty_target_cell_with_numeric_sources(self):
        """Should replicate even if target cell is empty, as long as sources are numeric."""
        grid = [
            ["Item", "2024", "2023"],
            ["Revenue", 100, 95],
            ["Cost", 40, 38],
            [
                "Profit",
                60,
                None,
            ],  # Target cell for col 2 is empty, but sources are numeric
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula="sum_col(0, 1, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        # Should replicate to col 2 even though target is None, because rows 1-2 in col 2 are numeric
        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }
        assert 2 in formulas_by_col
        assert formulas_by_col[2] == "sum_col(0, 2, 1, 2)"

    def test_sum_col_no_replication_to_non_numeric_column(self):
        """Should NOT replicate to columns without numeric values in the source range."""
        grid = [
            ["Item", "2024", "Notes"],
            ["Revenue", 100, "Good"],
            ["Cost", 40, "High"],
            ["Profit", 60, "OK"],
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula="sum_col(0, 1, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        # Should only have column 1 (original), not column 2 (non-numeric)
        cols = [r.target_cell.col_index for r in result]
        assert 1 in cols
        assert 2 not in cols

    def test_sum_col_no_backward_replication(self):
        """Should NOT replicate to numeric columns before the anchor column."""
        grid = [
            ["Item", "2022", "2023", "2024"],
            ["Revenue", 80, 90, 100],
            ["Cost", 32, 36, 40],
            ["Profit", 48, 54, 60],
        ]
        table_grids = {0: grid}

        # Anchor at col 2 — col 1 is numeric but comes before anchor
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=2),
            formula="sum_col(0, 2, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        cols = [r.target_cell.col_index for r in result]
        assert 2 in cols  # Original
        assert 3 in cols  # Forward replication
        assert 1 not in cols  # No backward replication

    def test_sum_cells_vertical(self):
        """Replicate vertical sum_cells formula."""
        grid = [
            ["Item", "2024", "2023"],
            ["Current Assets", 100, 95],
            ["Subtotal Current", 100, 95],
            ["Non-Current Assets", 50, 48],
            ["Subtotal Non-Current", 50, 48],
            ["Total Assets", 150, 143],  # Row 5 = row 2 + row 4
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=1),
            formula="sum_cells((0, 2, 1), (0, 4, 1))",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        # target_cell object has .col_index
        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }
        assert formulas_by_col[1] == "sum_cells((0, 2, 1), (0, 4, 1))"
        assert formulas_by_col[2] == "sum_cells((0, 2, 2), (0, 4, 2))"

    def test_sum_cells_vertical_no_backward_replication(self):
        """Vertical sum_cells should NOT replicate to columns before anchor."""
        grid = [
            ["Item", "2022", "2023", "2024"],
            ["A", 10, 20, 30],
            ["Sub A", 10, 20, 30],
            ["B", 5, 8, 12],
            ["Sub B", 5, 8, 12],
            ["Total", 15, 28, 42],
        ]
        table_grids = {0: grid}

        # Anchor at col 2 — col 1 is numeric but comes before anchor
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=2),
            formula="sum_cells((0, 2, 2), (0, 4, 2))",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        cols = [r.target_cell.col_index for r in result]
        assert 2 in cols  # Original
        assert 3 in cols  # Forward replication
        assert 1 not in cols  # No backward replication


class TestHorizontalReplication:
    """Test horizontal (row-based) formula replication."""

    def test_sum_row_basic(self):
        """Replicate sum_row formula to other rows."""
        grid = [
            ["Item", "Q1", "Q2", "Q3", "Total"],
            ["Revenue", 25, 30, 35, 90],  # Row 1: total in col 4
            ["Cost", 10, 12, 14, 36],  # Row 2: total in col 4
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=4),
            formula="sum_row(0, 1, 1, 3)",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        # Should get formulas for rows 1, 2
        assert len(result) == 2
        formulas_by_row = {
            r.target_cell.row_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_row[1] == "sum_row(0, 1, 1, 3)"  # Original
        assert formulas_by_row[2] == "sum_row(0, 2, 1, 3)"  # Replicated to row 2

    def test_sum_row_empty_target_with_numeric_sources(self):
        """Should replicate even if target cell is empty, sources are numeric."""
        grid = [
            ["Item", "Q1", "Q2", "Total"],
            ["Revenue", 25, 30, 55],
            ["Cost", 10, 12, None],  # Target empty but sources numeric
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=3),
            formula="sum_row(0, 1, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        formulas_by_row = {
            r.target_cell.row_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }
        assert 2 in formulas_by_row  # Should replicate even with empty target
        assert formulas_by_row[2] == "sum_row(0, 2, 1, 2)"

    def test_sum_row_no_replication_to_non_numeric_row(self):
        """Should NOT replicate to rows without numeric values in source range."""
        grid = [
            ["Item", "Q1", "Q2", "Total"],
            ["Revenue", 25, 30, 55],
            ["Notes", "Good", "Better", "N/A"],  # Non-numeric row
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=3),
            formula="sum_row(0, 1, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        rows = [r.target_cell.row_index for r in result]
        assert 1 in rows
        assert 2 not in rows  # Row 2 has non-numeric sources

    def test_sum_row_no_backward_replication(self):
        """Should NOT replicate to numeric rows before the anchor row."""
        grid = [
            ["Item", "Q1", "Q2", "Total"],
            ["Revenue", 25, 30, 55],
            ["Cost", 10, 12, 22],
            ["Tax", 5, 6, 11],
        ]
        table_grids = {0: grid}

        # Anchor at row 2 — row 1 is numeric but comes before anchor
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=2, col_index=3),
            formula="sum_row(0, 2, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        rows = [r.target_cell.row_index for r in result]
        assert 2 in rows  # Original
        assert 3 in rows  # Forward replication
        assert 1 not in rows  # No backward replication

    def test_sum_cells_horizontal(self):
        """Replicate horizontal sum_cells formula."""
        grid = [
            ["Item", "Base", "Adjust", "Total"],
            ["Revenue", 100, 10, 110],  # Col 3 = col 1 + col 2
            ["Cost", 40, 5, 45],
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=3),
            formula="sum_cells((0, 1, 1), (0, 1, 2))",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        formulas_by_row = {
            r.target_cell.row_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }
        assert formulas_by_row[1] == "sum_cells((0, 1, 1), (0, 1, 2))"
        assert formulas_by_row[2] == "sum_cells((0, 2, 1), (0, 2, 2))"

    def test_sum_cells_horizontal_no_backward_replication(self):
        """Horizontal sum_cells should NOT replicate to rows before anchor."""
        grid = [
            ["Item", "Base", "Adjust", "Total"],
            ["Revenue", 100, 10, 110],
            ["Cost", 40, 5, 45],
            ["Tax", 20, 3, 23],
        ]
        table_grids = {0: grid}

        # Anchor at row 2 — row 1 is numeric but comes before anchor
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=2, col_index=3),
            formula="sum_cells((0, 2, 1), (0, 2, 2))",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        rows = [r.target_cell.row_index for r in result]
        assert 2 in rows  # Original
        assert 3 in rows  # Forward replication
        assert 1 not in rows  # No backward replication


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_formula_list(self):
        """Should handle empty input gracefully."""
        result = replicate_formulas([], {0: [[1, 2], [3, 4]]})
        assert result == []

    def test_missing_table_grid(self):
        """Should skip replication if table grid not found."""
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=99, row_index=1, col_index=1),
            formula="sum_col(99, 1, 0, 1)",
        )

        result = replicate_formulas([anchor], {0: [[1, 2]]})

        # Should only contain original (no replication)
        assert len(result) == 1
        item = result[0]
        assert isinstance(item, HorizontalVerticalCheckInferredFormula)
        assert item.formula == "sum_col(99, 1, 0, 1)"

    def test_deduplication(self):
        """Should deduplicate identical formulas."""
        grid = [["", "A", "B"], [1, 100, 200], [2, 300, 400]]
        table_grids = {0: grid}

        # Two identical anchors
        anchor1 = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=2, col_index=1),
            formula="sum_col(0, 1, 1, 1)",
        )
        anchor2 = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=2, col_index=1),
            formula="sum_col(0, 1, 1, 1)",
        )

        result = replicate_formulas(
            [anchor1, anchor2], table_grids, direction="vertical"
        )

        # Should only have unique formulas
        keys = set()
        for r in result:
            t = r.target_cell
            if isinstance(r, HorizontalVerticalCheckInferredFormula):
                keys.add(((t.table_index, t.row_index, t.col_index), r.formula))
        assert len(result) == len(keys)
        assert len(result) == 2  # Original + replicated to col 2

    def test_mixed_vertical_and_horizontal(self):
        """Should handle both vertical and horizontal formulas in same batch."""
        grid = [
            ["Item", "Q1", "Q2", "Total"],
            ["Revenue", 100, 95, 195],
            ["Cost", 40, 38, 78],
            ["Profit", 60, 57, 117],
        ]
        table_grids = {0: grid}

        vertical_anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula="sum_col(0, 1, 1, 2)",
        )

        horizontal_anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=3),
            formula="sum_row(0, 1, 1, 2)",
        )

        res_v = replicate_formulas([vertical_anchor], table_grids, direction="vertical")
        res_h = replicate_formulas(
            [horizontal_anchor], table_grids, direction="horizontal"
        )
        result = res_v + res_h
        # Should have both types replicated
        vertical_formulas = [
            r
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
            and "sum_col" in r.formula
        ]
        horizontal_formulas = [
            r
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
            and "sum_row" in r.formula
        ]

        assert len(vertical_formulas) > 1
        assert len(horizontal_formulas) > 1

    def test_partially_numeric_column(self):
        """Should replicate to columns with at least ONE numeric value in range."""
        grid = [
            ["Item", "2024", "Mixed"],
            ["Revenue", 100, "N/A"],
            ["Cost", 40, 38],  # Row 2 col 2 is numeric
            ["Profit", 60, None],
        ]
        table_grids = {0: grid}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula="sum_col(0, 1, 1, 2)",  # Rows 1-2
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        cols = [r.target_cell.col_index for r in result]
        # Should replicate to col 2 because row 2 col 2 is numeric (38)
        assert 2 in cols


from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.formula_replicator import (
    detect_replication_direction,
)


class TestDirectionDetection:
    """Test detect_replication_direction logic."""

    def test_detect_vertical(self):
        """Should detect vertical direction (same column)."""
        # (t, r, c) format
        formula = "sum_cells((0, 1, 2), (0, 3, 2), (0, 5, 2))"
        target = TargetCell(table_index=0, row_index=6, col_index=2)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) == "vertical"

    def test_detect_horizontal(self):
        """Should detect horizontal direction (same row)."""
        formula = "sum_cells((0, 1, 2), (0, 1, 4), (0, 1, 6))"
        target = TargetCell(table_index=0, row_index=1, col_index=8)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) == "horizontal"

    def test_detect_mixed_none(self):
        """Should return None for mixed dimensions (span both rows and cols)."""
        # Cells: (0, 1, 2) and (0, 2, 3) -> different rows (1,2) AND different cols (2,3)
        formula = "sum_cells((0, 1, 2), (0, 2, 3))"
        target = TargetCell(table_index=0, row_index=3, col_index=3)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) is None

    def test_detect_single_cell_none_for_sum_cells(self):
        """Should return None for single cell sum_cells (ambiguous or invalid)."""
        formula = "sum_cells((0, 1, 2))"
        target = TargetCell(table_index=0, row_index=2, col_index=2)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        # _all_refs_same_column and _all_refs_same_row both return False for < 2 cells
        assert detect_replication_direction(item) is None

    def test_detect_cell_vertical(self):
        """Should detect vertical check if columns match."""
        # Target: Row 8, Col 1. Source: Row 5, Col 1.
        # Same column -> vertical logic check.
        formula = "cell(0, 5, 1)"
        target = TargetCell(table_index=0, row_index=8, col_index=1)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) == "vertical"

    def test_detect_cell_horizontal(self):
        """Should detect horizontal check if rows match."""
        # Target: Row 8, Col 5. Source: Row 8, Col 2.
        # Same row -> horizontal logic check.
        formula = "cell(0, 8, 2)"
        target = TargetCell(table_index=0, row_index=8, col_index=5)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) == "horizontal"

    def test_detect_cell_mixed_none(self):
        """Should return None if neither row nor column matches."""
        # Target: Row 8, Col 5. Source: Row 7, Col 4.
        # Diagonal / unrelated.
        formula = "cell(0, 7, 4)"
        target = TargetCell(table_index=0, row_index=8, col_index=5)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) is None


class TestCellFormulaReplication:
    """Test replication of cell() formulas."""

    def test_replicate_cell_vertical(self):
        """Should replicate cell() formula to other columns (vertical)."""
        # Grid:
        # R1: 10, 20, 30
        # R2: 10, 20, 30
        # Check: R2 = R1.
        grid = [
            ["Item", "C1", "C2", "C3"],
            ["R1", 10, 20, 30],
            ["R2", 10, 20, 30],
        ]
        table_grids = {0: grid}

        # Anchor: Col 1 checking Row 2 == Row 1
        target = TargetCell(table_index=0, row_index=2, col_index=1)
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula="cell(0, 1, 1)"
        )

        # Replicate vertical
        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        # Col 1: cell(0, 1, 1) (Original)
        assert formulas_by_col[1] == "cell(0, 1, 1)"
        # Col 2: cell(0, 1, 2)
        assert formulas_by_col[2] == "cell(0, 1, 2)"
        # Col 3: cell(0, 1, 3)
        assert formulas_by_col[3] == "cell(0, 1, 3)"

    def test_replicate_cell_horizontal(self):
        """Should replicate cell() formula to other rows (horizontal)."""
        # Grid:
        # C1, C2
        # 10, 10
        # 20, 20
        # Check: C2 = C1.
        grid = [
            ["Item", "C1", "C2"],
            ["R1", 10, 10],
            ["R2", 20, 20],
        ]
        table_grids = {0: grid}

        # Anchor: Row 1 checking C2 == C1
        target = TargetCell(table_index=0, row_index=1, col_index=2)
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula="cell(0, 1, 1)"
        )

        # Replicate horizontal
        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        formulas_by_row = {
            r.target_cell.row_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        # Row 1: cell(0, 1, 1) (Original)
        assert formulas_by_row[1] == "cell(0, 1, 1)"
        # Row 2: cell(0, 2, 1)
        assert formulas_by_row[2] == "cell(0, 2, 1)"


class TestLogicReplication:
    """Test logic reconciliation multi-formula replication."""

    def test_replicate_logic_multi_formulas(self):
        """Should replicate each formula in a multi-formula LogicInferredFormula."""
        grid = [
            ["Item", "C1", "C2", "C3"],
            ["R1", 10, 11, 12],
            ["R2", 20, 21, 22],
            ["Total", 30, 32, 34],
        ]
        table_grids = {0: grid}

        # Item with 2 formulas
        item = LogicInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formulas=["sum_col(0, 1, 1, 2)", "cell(0, 1, 1)"],
        )

        # Replicate vertically
        results = replicate_formulas([item], table_grids, direction="vertical")

        assert len(results) == 6

        col2_formulas = [
            f.formulas[0]
            for f in results
            if f.target_cell.col_index == 2 and isinstance(f, LogicInferredFormula)
        ]
        assert "sum_col(0, 2, 1, 2)" in col2_formulas
        assert "cell(0, 1, 2)" in col2_formulas

        # Verify all results are LogicInferredFormula
        for r in results:
            assert isinstance(r, LogicInferredFormula)
            assert len(r.formulas) == 1


class TestArithmeticVerticalReplication:
    """Test vertical replication of compound arithmetic formulas.

    These formulas come from the Logic Reconciliation agent which produces
    sign-variant formulas like:
      cell(0, 7, 3) + cell(0, 12, 3)
      cell(0, 1, 3) + cell(0, 5, 3) - cell(0, 9, 3)
    """

    GRID: ClassVar[list] = [
        # Row 0: headers
        ["Item", "2024", "2023", "2022"],
        # Row 1: Opening cost
        ["Opening cost", 1000, 900, 800],
        # Row 2: Additions
        ["Additions", 200, 150, 100],
        # Row 3: Disposals
        ["Disposals", -50, -30, -20],
        # Row 4: Transfers
        ["Transfers", 30, 20, 10],
        # Row 5: Closing cost (= opening + additions - disposals + transfers)
        ["Closing cost", 1180, 1040, 890],
        # Row 6: Accum depr opening
        ["AD Opening", -300, -250, -200],
        # Row 7: Depreciation charge
        ["Depr charge", -100, -80, -60],
        # Row 8: AD of disposals
        ["AD Disposals", 20, 10, 5],
        # Row 9: AD Closing (= AD opening + depr + AD disposals)
        ["AD Closing", -380, -320, -255],
        # Row 10: Carrying amount (= closing cost + AD closing)
        ["Carrying amt", 800, 720, 635],
    ]

    def test_addition_two_cells_vertical(self):
        """cell(0, 1, 1) + cell(0, 2, 1) should replicate across columns."""
        table_grids = {0: self.GRID}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=1),
            formula="cell(0, 1, 1) + cell(0, 2, 1)",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[1] == "cell(0, 1, 1) + cell(0, 2, 1)"  # Original
        assert formulas_by_col[2] == "cell(0, 1, 2) + cell(0, 2, 2)"
        assert formulas_by_col[3] == "cell(0, 1, 3) + cell(0, 2, 3)"

    def test_subtraction_preserved_vertical(self):
        """cell(0, 5, 1) - cell(0, 3, 1) must keep the minus sign."""
        table_grids = {0: self.GRID}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=10, col_index=1),
            formula="cell(0, 5, 1) - cell(0, 3, 1)",
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[1] == "cell(0, 5, 1) - cell(0, 3, 1)"
        assert formulas_by_col[2] == "cell(0, 5, 2) - cell(0, 3, 2)"
        assert formulas_by_col[3] == "cell(0, 5, 3) - cell(0, 3, 3)"

    def test_mixed_operators_vertical(self):
        """cell() + cell() - cell() + cell() preserves all operators."""
        table_grids = {0: self.GRID}

        # Closing cost = opening + additions - disposals + transfers
        formula = "cell(0, 1, 1) + cell(0, 2, 1) - cell(0, 3, 1) + cell(0, 4, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[1] == formula
        assert (
            formulas_by_col[2]
            == "cell(0, 1, 2) + cell(0, 2, 2) - cell(0, 3, 2) + cell(0, 4, 2)"
        )
        assert (
            formulas_by_col[3]
            == "cell(0, 1, 3) + cell(0, 2, 3) - cell(0, 3, 3) + cell(0, 4, 3)"
        )

    def test_parenthesized_arithmetic_vertical(self):
        """(cell() + cell()) - cell() preserves parentheses."""
        table_grids = {0: self.GRID}

        formula = "(cell(0, 1, 1) + cell(0, 2, 1)) - cell(0, 3, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[2] == "(cell(0, 1, 2) + cell(0, 2, 2)) - cell(0, 3, 2)"

    def test_no_replication_mixed_columns(self):
        """Arithmetic with cells in different columns should NOT replicate."""
        table_grids = {0: self.GRID}

        # Columns 1 and 2 are mixed -> can't determine a single anchor column
        formula = "cell(0, 1, 1) + cell(0, 1, 2)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        # Should only contain the original, no replicas
        assert len(result) == 1
        assert isinstance(result[0], HorizontalVerticalCheckInferredFormula)
        assert result[0].formula == formula

    def test_no_replication_single_cell_arithmetic(self):
        """A formula with only one cell() ref should not be handled by arithmetic replicator."""
        table_grids = {0: self.GRID}

        # Single cell gets handled by the cell() fullmatch path, not arithmetic
        formula = "cell(0, 1, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        # Should replicate via the single-cell path (3 cols: 1, 2, 3)
        assert len(result) == 3
        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }
        assert formulas_by_col[1] == "cell(0, 1, 1)"
        assert formulas_by_col[2] == "cell(0, 1, 2)"
        assert formulas_by_col[3] == "cell(0, 1, 3)"

    def test_no_backward_replication_arithmetic(self):
        """Arithmetic replication should NOT replicate to columns before anchor."""
        table_grids = {0: self.GRID}

        # Anchor at col 2
        formula = "cell(0, 1, 2) + cell(0, 2, 2)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=5, col_index=2),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        cols = [r.target_cell.col_index for r in result]
        assert 2 in cols  # Original
        assert 3 in cols  # Forward
        assert 1 not in cols  # No backward

    def test_arithmetic_stops_at_non_numeric_column(self):
        """Should NOT replicate to columns where all referenced cells are non-numeric."""
        grid = [
            ["Item", "2024", "Notes"],
            ["Opening", 1000, "start"],
            ["Additions", 200, "new"],
            ["Closing", 1200, "end"],
        ]
        table_grids = {0: grid}

        formula = "cell(0, 1, 1) + cell(0, 2, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        cols = [r.target_cell.col_index for r in result]
        assert 1 in cols  # Original
        assert 2 not in cols  # Non-numeric

    def test_logic_inferred_arithmetic_vertical(self):
        """LogicInferredFormula with arithmetic should replicate as LogicInferredFormula."""
        table_grids = {0: self.GRID}

        item = LogicInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=10, col_index=1),
            formulas=["cell(0, 5, 1) + cell(0, 9, 1)"],
        )

        results = replicate_formulas([item], table_grids, direction="vertical")

        # All results should be LogicInferredFormula
        for r in results:
            assert isinstance(r, LogicInferredFormula)

        formulas_by_col = {
            r.target_cell.col_index: r.formulas[0]
            for r in results
            if isinstance(r, LogicInferredFormula)
        }

        assert formulas_by_col[1] == "cell(0, 5, 1) + cell(0, 9, 1)"
        assert formulas_by_col[2] == "cell(0, 5, 2) + cell(0, 9, 2)"
        assert formulas_by_col[3] == "cell(0, 5, 3) + cell(0, 9, 3)"

    def test_real_world_bug_formula(self):
        """Regression: cell(0, 7, 3) + cell(0, 12, 3) must NOT be truncated.

        The original bug: CELL_FUNC_PATTERN.match() only matched the first
        cell() reference, producing a truncated replica like cell(0, 7, 4).
        After the fix, this should replicate the full arithmetic expression.
        """
        grid = [
            # 5 columns: label + 3 numeric + 1 non-numeric
            ["Item", "Col1", "Col2", "Col3", "Col4"],
            *[[f"Row{i}", 10, 20, 30, 40] for i in range(1, 14)],
        ]
        table_grids = {0: grid}

        formula = "cell(0, 7, 3) + cell(0, 12, 3)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=13, col_index=3),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        # Original
        assert formulas_by_col[3] == "cell(0, 7, 3) + cell(0, 12, 3)"
        # Replicated — must be full arithmetic, NOT truncated "cell(0, 7, 4)"
        assert formulas_by_col[4] == "cell(0, 7, 4) + cell(0, 12, 4)"


class TestArithmeticHorizontalReplication:
    """Test horizontal replication of compound arithmetic formulas."""

    GRID: ClassVar[list] = [
        ["Item", "Base", "Adjust1", "Adjust2", "Total"],
        ["Revenue", 100, 10, 5, 115],
        ["Cost", 40, 3, 2, 45],
        ["Tax", 15, 1, 1, 17],
    ]

    def test_addition_two_cells_horizontal(self):
        """cell(0, 1, 1) + cell(0, 1, 2) should replicate across rows."""
        table_grids = {0: self.GRID}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=4),
            formula="cell(0, 1, 1) + cell(0, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        formulas_by_row = {
            r.target_cell.row_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_row[1] == "cell(0, 1, 1) + cell(0, 1, 2)"
        assert formulas_by_row[2] == "cell(0, 2, 1) + cell(0, 2, 2)"
        assert formulas_by_row[3] == "cell(0, 3, 1) + cell(0, 3, 2)"

    def test_subtraction_preserved_horizontal(self):
        """cell(0, 1, 1) - cell(0, 1, 2) must keep the minus sign when replicated."""
        table_grids = {0: self.GRID}

        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=4),
            formula="cell(0, 1, 1) - cell(0, 1, 2)",
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        formulas_by_row = {
            r.target_cell.row_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_row[2] == "cell(0, 2, 1) - cell(0, 2, 2)"
        assert formulas_by_row[3] == "cell(0, 3, 1) - cell(0, 3, 2)"

    def test_mixed_operators_horizontal(self):
        """cell() + cell() + cell() - preserves all operators across rows."""
        table_grids = {0: self.GRID}

        formula = "cell(0, 1, 1) + cell(0, 1, 2) + cell(0, 1, 3)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=4),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        formulas_by_row = {
            r.target_cell.row_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_row[2] == "cell(0, 2, 1) + cell(0, 2, 2) + cell(0, 2, 3)"

    def test_no_replication_mixed_rows(self):
        """Arithmetic with cells in different rows should NOT replicate horizontally."""
        table_grids = {0: self.GRID}

        # Rows 1 and 2 mixed -> can't determine single anchor row
        formula = "cell(0, 1, 1) + cell(0, 2, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=1, col_index=4),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        # Only original, no replicas
        assert len(result) == 1

    def test_no_backward_replication_arithmetic_horizontal(self):
        """Arithmetic horizontal should NOT replicate to rows before anchor."""
        table_grids = {0: self.GRID}

        # Anchor at row 2
        formula = "cell(0, 2, 1) + cell(0, 2, 2)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=2, col_index=4),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="horizontal")

        rows = [r.target_cell.row_index for r in result]
        assert 2 in rows  # Original
        assert 3 in rows  # Forward
        assert 1 not in rows  # No backward


class TestDirectionDetectionCompoundFormulas:
    """Test detect_replication_direction for compound arithmetic formulas."""

    def test_detect_vertical_compound(self):
        """Compound formula with all same-column cells -> vertical."""
        formula = "cell(0, 1, 2) + cell(0, 5, 2) - cell(0, 9, 2)"
        target = TargetCell(table_index=0, row_index=10, col_index=2)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) == "vertical"

    def test_detect_horizontal_compound(self):
        """Compound formula with all same-row cells -> horizontal."""
        formula = "cell(0, 3, 1) + cell(0, 3, 2) - cell(0, 3, 4)"
        target = TargetCell(table_index=0, row_index=3, col_index=5)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) == "horizontal"

    def test_detect_mixed_compound_none(self):
        """Compound formula with mixed rows AND columns -> None."""
        formula = "cell(0, 1, 2) + cell(0, 3, 4)"
        target = TargetCell(table_index=0, row_index=5, col_index=5)
        item = HorizontalVerticalCheckInferredFormula(
            target_cell=target, formula=formula
        )
        assert detect_replication_direction(item) is None

    def test_detect_logic_inferred_compound(self):
        """LogicInferredFormula with compound arithmetic should detect direction."""
        formula = "cell(0, 7, 3) + cell(0, 12, 3)"
        target = TargetCell(table_index=0, row_index=13, col_index=3)
        item = LogicInferredFormula(target_cell=target, formulas=[formula])
        assert detect_replication_direction(item) == "vertical"


class TestArithmeticEdgeCases:
    """Test edge cases for compound arithmetic replication.

    Covers: abs() wrapping, cross-table references, whitespace variations,
    multiplication/division operators.
    """

    def test_abs_wrapped_arithmetic_vertical(self):
        """abs(cell() - cell()) should replicate preserving the abs() wrapper."""
        grid = [
            ["Item", "2024", "2023"],
            ["Revenue", 100, 95],
            ["Cost", 40, 38],
            ["Diff", 60, 57],
        ]
        table_grids = {0: grid}

        formula = "abs(cell(0, 1, 1) - cell(0, 2, 1))"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[1] == "abs(cell(0, 1, 1) - cell(0, 2, 1))"
        assert formulas_by_col[2] == "abs(cell(0, 1, 2) - cell(0, 2, 2))"

    def test_cross_table_arithmetic_vertical(self):
        """cell(0, ...) + cell(1, ...) with same column should replicate."""
        grid_0 = [
            ["Item", "2024", "2023"],
            ["BS Cash", 500, 400],
        ]
        grid_1 = [
            ["Item", "2024", "2023"],
            ["Note Cash", 300, 250],
            ["Total", 800, 650],
        ]
        table_grids = {0: grid_0, 1: grid_1}

        formula = "cell(0, 1, 1) + cell(1, 1, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=1, row_index=2, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[1] == "cell(0, 1, 1) + cell(1, 1, 1)"
        assert formulas_by_col[2] == "cell(0, 1, 2) + cell(1, 1, 2)"

    def test_no_whitespace_arithmetic_vertical(self):
        """cell(0,1,1)+cell(0,2,1) with no spaces should replicate correctly.

        Note: re.sub rewrites cell() refs with canonical spacing in replicas,
        which is fine since the formula engine handles both forms.
        """
        grid = [
            ["Item", "2024", "2023"],
            ["A", 100, 95],
            ["B", 200, 190],
            ["Total", 300, 285],
        ]
        table_grids = {0: grid}

        formula = "cell(0,1,1)+cell(0,2,1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[1] == "cell(0,1,1)+cell(0,2,1)"
        # Replicas get canonical spacing from re.sub, which is fine for eval
        assert formulas_by_col[2] == "cell(0, 1, 2)+cell(0, 2, 2)"

    def test_extra_whitespace_arithmetic_vertical(self):
        """cell( 0 , 1 , 1 ) + cell( 0 , 2 , 1 ) with extra spaces should replicate."""
        grid = [
            ["Item", "2024", "2023"],
            ["A", 100, 95],
            ["B", 200, 190],
            ["Total", 300, 285],
        ]
        table_grids = {0: grid}

        formula = "cell( 0 , 1 , 1 ) + cell( 0 , 2 , 1 )"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        # Should have replicated (original + col 2)
        assert len(result) == 2
        replica = next(r for r in result if r.target_cell.col_index == 2)
        # The re.sub rewrites cell() refs with canonical spacing
        assert isinstance(replica, HorizontalVerticalCheckInferredFormula)
        assert "cell(0, 1, 2)" in replica.formula
        assert "cell(0, 2, 2)" in replica.formula

    def test_multiplication_operator_vertical(self):
        """cell() * cell() should replicate preserving the * operator."""
        grid = [
            ["Item", "2024", "2023"],
            ["Price", 10, 9],
            ["Qty", 5, 4],
            ["Total", 50, 36],
        ]
        table_grids = {0: grid}

        formula = "cell(0, 1, 1) * cell(0, 2, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[2] == "cell(0, 1, 2) * cell(0, 2, 2)"

    def test_division_operator_vertical(self):
        """cell() / cell() should replicate preserving the / operator."""
        grid = [
            ["Item", "2024", "2023"],
            ["Revenue", 100, 90],
            ["Units", 10, 9],
            ["Per Unit", 10, 10],
        ]
        table_grids = {0: grid}

        formula = "cell(0, 1, 1) / cell(0, 2, 1)"
        anchor = HorizontalVerticalCheckInferredFormula(
            target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
            formula=formula,
        )

        result = replicate_formulas([anchor], table_grids, direction="vertical")

        formulas_by_col = {
            r.target_cell.col_index: r.formula
            for r in result
            if isinstance(r, HorizontalVerticalCheckInferredFormula)
        }

        assert formulas_by_col[2] == "cell(0, 1, 2) / cell(0, 2, 2)"
