"""Unit tests for in_table_pipeline callbacks.

Tests cover:
- Collecting outputs from vertical and horizontal agents
- Formula replication
- Actual value lookup
- State management
"""

from unittest.mock import MagicMock

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.callbacks import (
    after_in_table_parallel_callback,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.schema import (
    CheckAgentOutput,
    InferredFormula,
    TargetCell,
)


class TestAfterInTableParallelCallback:
    """Test the post-processing callback for in-table pipeline."""

    def test_no_tables_in_state(self):
        """Should handle missing extracted_tables gracefully."""
        ctx = MagicMock()
        ctx.state = {}

        after_in_table_parallel_callback(ctx)

        assert ctx.state.get("reconstructed_formulas") == []

    def test_empty_tables_list(self):
        """Should handle empty tables list."""
        ctx = MagicMock()
        ctx.state = {"extracted_tables": {"tables": []}}

        after_in_table_parallel_callback(ctx)

        assert ctx.state.get("reconstructed_formulas") == []

    def test_collect_vertical_formulas(self):
        """Should collect formulas from vertical check agent."""
        grid = [
            ["Item", "2024", "2023"],
            ["Revenue", 100, 95],
            ["Cost", 40, 38],
            ["Profit", 60, 57],
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
                        formula="sum_col(0, 1, 1, 2)",
                    )
                ]
            ),
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        # Should have original + replicated for columns 1 and 2
        assert len(formulas) >= 2

        # Check all are vertical and in-table
        # Check check_type is in-table
        for f in formulas:
            assert f["check_type"] == "in_table"

    def test_collect_horizontal_formulas(self):
        """Should collect formulas from horizontal check agent."""
        grid = [
            ["Item", "Q1", "Q2", "Total"],
            ["Revenue", 100, 95, 195],
            ["Cost", 40, 38, 78],
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "horizontal_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=1, col_index=3),
                        formula="sum_row(0, 1, 1, 2)",
                    )
                ]
            ),
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        # Should have replicated to both rows
        assert len(formulas) >= 2

        for f in formulas:
            assert f["check_type"] == "in_table"

    def test_actual_value_lookup(self):
        """Should populate actual_value from target_cell."""
        grid = [
            ["Item", "2024"],
            ["Revenue", 100],
            ["Cost", 40],
            ["Profit", 60],
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
                        formula="sum_col(0, 1, 1, 2)",
                    )
                ]
            ),
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        # Find the formula for target_cell (0, 3, 1)
        target_formula = next(
            f
            for f in formulas
            if f["target_cells"][0]["table_index"] == 0
            and f["target_cells"][0]["row_index"] == 3
            and f["target_cells"][0]["col_index"] == 1
        )

        # Should have actual_value from grid[3][1] = 60
        assert target_formula["actual_value"] == 60.0

    def test_actual_value_none_for_empty_cell(self):
        """Should set actual_value to None if target cell is empty."""
        grid = [
            ["Item", "2024"],
            ["Revenue", 100],
            ["Cost", 40],
            ["Profit", None],  # Empty target cell
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
                        formula="sum_col(0, 1, 1, 2)",
                    )
                ]
            ),
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        target_formula = next(
            f
            for f in formulas
            if f["target_cells"][0]["table_index"] == 0
            and f["target_cells"][0]["row_index"] == 3
            and f["target_cells"][0]["col_index"] == 1
        )

        assert target_formula["actual_value"] is None

    def test_actual_value_none_for_non_numeric(self):
        """Should set actual_value to None if target cell is not numeric."""
        grid = [
            ["Item", "2024"],
            ["Revenue", 100],
            ["Cost", 40],
            ["Profit", "N/A"],  # Non-numeric
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
                        formula="sum_col(0, 1, 1, 2)",
                    )
                ]
            ),
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        target_formula = next(
            f
            for f in formulas
            if f["target_cells"][0]["table_index"] == 0
            and f["target_cells"][0]["row_index"] == 3
            and f["target_cells"][0]["col_index"] == 1
        )

        assert target_formula["actual_value"] is None

    def test_both_vertical_and_horizontal(self):
        """Should handle both vertical and horizontal formulas."""
        grid = [
            ["Item", "Q1", "Q2", "Total"],
            ["Revenue", 100, 95, 195],
            ["Cost", 40, 38, 78],
            ["Profit", 60, 57, 117],
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
                        formula="sum_col(0, 1, 1, 2)",
                    )
                ]
            ),
            "horizontal_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=1, col_index=3),
                        formula="sum_row(0, 1, 1, 2)",
                    )
                ]
            ),
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]

        vertical_formulas = [
            f for f in formulas if "sum_col" in f["inferred_formulas"][0]["formula"]
        ]
        horizontal_formulas = [
            f for f in formulas if "sum_row" in f["inferred_formulas"][0]["formula"]
        ]

        assert len(vertical_formulas) > 0
        assert len(horizontal_formulas) > 0

    def test_handles_dict_output(self):
        """Should handle outputs that are already dicts (not Pydantic models)."""
        grid = [["Item", "Val"], ["A", 100], ["Total", 100]]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": {
                "formulas": [
                    {
                        "target_cell": {
                            "table_index": 0,
                            "row_index": 2,
                            "col_index": 1,
                        },
                        "formula": "sum_col(0, 1, 1, 1)",
                        "check_type": "vertical",
                    }
                ]
            },
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        assert len(formulas) > 0

    def test_output_schema_structure(self):
        """Verify the output structure matches expected schema."""
        grid = [["Item", "2024"], ["Revenue", 100], ["Total", 100]]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": CheckAgentOutput(
                formulas=[
                    InferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=2, col_index=1),
                        formula="sum_col(0, 1, 1, 1)",
                    )
                ]
            ),
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        assert len(formulas) > 0

        # Check schema of first formula
        f = formulas[0]
        assert f["check_type"] == "in_table"
        assert "table_index" in f
        assert "target_cells" in f
        assert isinstance(f["target_cells"], list)
        assert "actual_value" in f
        assert "inferred_formulas" in f
        assert isinstance(f["inferred_formulas"], list)
        assert "formula" in f["inferred_formulas"][0]

    def test_ignores_malformed_formulas(self):
        """Should skip formulas with missing required fields."""
        grid = [["Item", "Val"], ["A", 100]]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": {
                "formulas": [
                    {"formula": "sum_col(0, 1, 0, 0)"},  # Missing target_cell
                    {
                        "target_cell": {
                            "table_index": 0,
                            "row_index": 1,
                            "col_index": 1,
                        },
                        "formula": "sum_col(0, 1, 0, 0)",
                        "check_type": "vertical",
                    },  # Valid
                ]
            },
        }

        after_in_table_parallel_callback(ctx)

        formulas = ctx.state["reconstructed_formulas"]
        # Should only have the valid formula
        assert len(formulas) == 1
