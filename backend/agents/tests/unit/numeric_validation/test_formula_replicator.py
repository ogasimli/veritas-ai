"""Unit tests for formula_replicator.py

Tests cover:
- Vertical replication (sum_col, sum_cells)
- Horizontal replication (sum_row, sum_cells)
- Edge cases: empty target cells, non-numeric source cells, etc.
"""

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.formula_replicator import (
    replicate_formulas,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.schema import (
    InferredFormula,
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

        anchor = InferredFormula(
            target_cell=(0, 3, 1),  # Row 3, Col 1 (2024 total)
            formula="sum_col(0, 1, 1, 2)",
            check_type="vertical",
        )

        result = replicate_formulas([anchor], table_grids)

        # Should get formulas for columns 1, 2, 3
        assert len(result) == 3
        formulas_by_col = {r.target_cell[2]: r.formula for r in result}

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

        anchor = InferredFormula(
            target_cell=(0, 3, 1),
            formula="sum_col(0, 1, 1, 2)",
            check_type="vertical",
        )

        result = replicate_formulas([anchor], table_grids)

        # Should replicate to col 2 even though target is None, because rows 1-2 in col 2 are numeric
        formulas_by_col = {r.target_cell[2]: r.formula for r in result}
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

        anchor = InferredFormula(
            target_cell=(0, 3, 1),
            formula="sum_col(0, 1, 1, 2)",
            check_type="vertical",
        )

        result = replicate_formulas([anchor], table_grids)

        # Should only have column 1 (original), not column 2 (non-numeric)
        cols = [r.target_cell[2] for r in result]
        assert 1 in cols
        assert 2 not in cols

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

        anchor = InferredFormula(
            target_cell=(0, 5, 1),
            formula="sum_cells((0, 2, 1), (0, 4, 1))",
            check_type="vertical",
        )

        result = replicate_formulas([anchor], table_grids)

        formulas_by_col = {r.target_cell[2]: r.formula for r in result}
        assert formulas_by_col[1] == "sum_cells((0, 2, 1), (0, 4, 1))"
        assert formulas_by_col[2] == "sum_cells((0, 2, 2), (0, 4, 2))"


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

        anchor = InferredFormula(
            target_cell=(0, 1, 4),  # Row 1, Col 4 (Revenue total)
            formula="sum_row(0, 1, 1, 3)",
            check_type="horizontal",
        )

        result = replicate_formulas([anchor], table_grids)

        # Should get formulas for rows 1, 2
        assert len(result) == 2
        formulas_by_row = {r.target_cell[1]: r.formula for r in result}

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

        anchor = InferredFormula(
            target_cell=(0, 1, 3),
            formula="sum_row(0, 1, 1, 2)",
            check_type="horizontal",
        )

        result = replicate_formulas([anchor], table_grids)

        formulas_by_row = {r.target_cell[1]: r.formula for r in result}
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

        anchor = InferredFormula(
            target_cell=(0, 1, 3),
            formula="sum_row(0, 1, 1, 2)",
            check_type="horizontal",
        )

        result = replicate_formulas([anchor], table_grids)

        rows = [r.target_cell[1] for r in result]
        assert 1 in rows
        assert 2 not in rows  # Row 2 has non-numeric sources

    def test_sum_cells_horizontal(self):
        """Replicate horizontal sum_cells formula."""
        grid = [
            ["Item", "Base", "Adjust", "Total"],
            ["Revenue", 100, 10, 110],  # Col 3 = col 1 + col 2
            ["Cost", 40, 5, 45],
        ]
        table_grids = {0: grid}

        anchor = InferredFormula(
            target_cell=(0, 1, 3),
            formula="sum_cells((0, 1, 1), (0, 1, 2))",
            check_type="horizontal",
        )

        result = replicate_formulas([anchor], table_grids)

        formulas_by_row = {r.target_cell[1]: r.formula for r in result}
        assert formulas_by_row[1] == "sum_cells((0, 1, 1), (0, 1, 2))"
        assert formulas_by_row[2] == "sum_cells((0, 2, 1), (0, 2, 2))"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_formula_list(self):
        """Should handle empty input gracefully."""
        result = replicate_formulas([], {0: [[1, 2], [3, 4]]})
        assert result == []

    def test_missing_table_grid(self):
        """Should skip replication if table grid not found."""
        anchor = InferredFormula(
            target_cell=(99, 1, 1),  # Table 99 doesn't exist
            formula="sum_col(99, 1, 0, 1)",
            check_type="vertical",
        )

        result = replicate_formulas([anchor], {0: [[1, 2]]})

        # Should only contain original (no replication)
        assert len(result) == 1
        assert result[0].formula == "sum_col(99, 1, 0, 1)"

    def test_deduplication(self):
        """Should deduplicate identical formulas."""
        grid = [["", "A", "B"], [1, 100, 200], [2, 300, 400]]
        table_grids = {0: grid}

        # Two identical anchors
        anchor1 = InferredFormula(
            target_cell=(0, 1, 1), formula="sum_col(0, 1, 0, 0)", check_type="vertical"
        )
        anchor2 = InferredFormula(
            target_cell=(0, 1, 1), formula="sum_col(0, 1, 0, 0)", check_type="vertical"
        )

        result = replicate_formulas([anchor1, anchor2], table_grids)

        # Should only have unique formulas
        unique_formulas = [(r.target_cell, r.formula) for r in result]
        assert len(unique_formulas) == len(set(unique_formulas))

    def test_mixed_vertical_and_horizontal(self):
        """Should handle both vertical and horizontal formulas in same batch."""
        grid = [
            ["Item", "Q1", "Q2", "Total"],
            ["Revenue", 100, 95, 195],
            ["Cost", 40, 38, 78],
            ["Profit", 60, 57, 117],
        ]
        table_grids = {0: grid}

        vertical_anchor = InferredFormula(
            target_cell=(0, 3, 1),
            formula="sum_col(0, 1, 1, 2)",
            check_type="vertical",
        )

        horizontal_anchor = InferredFormula(
            target_cell=(0, 1, 3),
            formula="sum_row(0, 1, 1, 2)",
            check_type="horizontal",
        )

        result = replicate_formulas([vertical_anchor, horizontal_anchor], table_grids)

        # Should have both types replicated
        vertical_formulas = [r for r in result if r.check_type == "vertical"]
        horizontal_formulas = [r for r in result if r.check_type == "horizontal"]

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

        anchor = InferredFormula(
            target_cell=(0, 3, 1),
            formula="sum_col(0, 1, 1, 2)",  # Rows 1-2
            check_type="vertical",
        )

        result = replicate_formulas([anchor], table_grids)

        cols = [r.target_cell[2] for r in result]
        # Should replicate to col 2 because row 2 col 2 is numeric (38)
        assert 2 in cols
