"""Unit tests for in_table_pipeline callbacks.

Tests cover:
- Collecting outputs from vertical and horizontal agents
- Formula replication
- Actual value lookup
- State management
"""

from unittest.mock import MagicMock, patch

from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.callbacks import (
    after_in_table_parallel_callback,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.schema import (
    TargetCell,
)
from veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.sub_agents.vertical_horizontal_check.schema import (
    HorizontalVerticalCheckAgentOutput,
    HorizontalVerticalCheckInferredFormula,
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
            "vertical_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
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
            "horizontal_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
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
            "vertical_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
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

    def test_actual_value_zero_for_empty_cell(self):
        """Should set actual_value to 0.0 if target cell is empty."""
        grid = [
            ["Item", "2024"],
            ["Revenue", 100],
            ["Cost", 40],
            ["Profit", None],  # Empty target cell
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
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

        assert target_formula["actual_value"] == 0.0

    def test_actual_value_zero_for_non_numeric(self):
        """Should set actual_value to 0.0 if target cell is not numeric."""
        grid = [
            ["Item", "2024"],
            ["Revenue", 100],
            ["Cost", 40],
            ["Profit", "N/A"],  # Non-numeric
        ]

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
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

        assert target_formula["actual_value"] == 0.0

    def test_actual_value_none_for_out_of_bounds(self):
        """Should set actual_value to None and log error for out-of-bounds target."""
        grid = [["Item", "2024"], ["A", 10]]
        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "vertical_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
                        target_cell=TargetCell(
                            table_index=0, row_index=5, col_index=1
                        ),  # Out of bounds
                        formula="sum_col(0, 1, 1, 1)",
                    )
                ]
            ),
        }

        with patch(
            "veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.callbacks.logger"
        ) as mock_logger:
            after_in_table_parallel_callback(ctx)

            # Should have logged an error
            assert mock_logger.error.called
            args = mock_logger.error.call_args[0]
            assert "out of bounds" in args[0]

            formulas = ctx.state["reconstructed_formulas"]
            assert formulas[0]["actual_value"] is None

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
            "vertical_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
                        target_cell=TargetCell(table_index=0, row_index=3, col_index=1),
                        formula="sum_col(0, 1, 1, 2)",
                    )
                ]
            ),
            "horizontal_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
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
            "vertical_check_output": HorizontalVerticalCheckAgentOutput(
                formulas=[
                    HorizontalVerticalCheckInferredFormula(
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


class TestDynamicReplication:
    """Test dynamic direction logic in logic_reconciliation_formula_inferer_output."""

    def test_dynamic_vertical_and_horizontal(self):
        """Should detect directions dynamically and replicate logic check formulas."""
        grid = [
            ["Item", "C1", "C2"],
            ["R1", 10, 10],
            ["R2", 20, 20],
            ["Total", 30, 30],
        ]
        # Table 0

        # Vertical formula: sum_cells((0,1,1), (0,2,1)) -> Col 1, Rows 1+2
        # Horizontal formula: sum_cells((0,1,1), (0,1,2)) -> cannot happen in this grid easily for rollforward,
        # but let's assume a valid horizontal pattern:
        # e.g. Row 1: 10, 10. Maybe sum_cells((0,1,1), (0,1,2))

        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": grid}]},
            "logic_reconciliation_formula_inferer_output": {
                "formulas": [
                    {
                        "target_cell": {
                            "table_index": 0,
                            "row_index": 3,
                            "col_index": 1,
                        },
                        "formula": "sum_cells((0, 1, 1), (0, 2, 1))",  # Vertical
                    },
                    {
                        "target_cell": {
                            "table_index": 0,
                            "row_index": 1,
                            "col_index": 1,
                        },
                        "formula": "sum_cells((0, 2, 1), (0, 2, 2))",  # Horizontal ref? No, let's make it clear horizontal
                        # sum_cells((0,2,1), (0,2,2)) -> Row 2, Cols 1 & 2
                    },
                ]
            },
        }

        # Override formula for horizontal to be clearly horizontal
        # Row 2 (R2): sum of Col 1 and Col 2? No, let's say Total Row is sum of rows.
        # Let's say we have a horizontal check: Row 1 Col 1 + Row 1 Col 2 (nonsense but structural check).

        # Clearer horizontal example:
        # sum_cells((0, 1, 1), (0, 1, 2)) -> cells in Row 1.
        ctx.state["logic_reconciliation_formula_inferer_output"]["formulas"][1][
            "formula"
        ] = "sum_cells((0, 1, 1), (0, 1, 2))"
        ctx.state["logic_reconciliation_formula_inferer_output"]["formulas"][1][
            "target_cell"
        ] = {"table_index": 0, "row_index": 1, "col_index": 0}

        with patch(
            "veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.callbacks.detect_replication_direction"
        ) as mock_detect:
            # We mock detect to ensure it's called
            def side_effect(f_item):
                f = f_item.formula
                if "(0, 1, 1), (0, 2, 1)" in f:
                    return "vertical"
                if "(0, 1, 1), (0, 1, 2)" in f:
                    return "horizontal"
                return None

            mock_detect.side_effect = side_effect

            # We also need real replication logic, which is imported in callbacks.
            # But since we patch mock_detect in the TEST file, we need to patch where it is USED.
            # The test imports `after_in_table_parallel_callback`.
            # That function imports `detect_sum_cells_direction` from `formula_replicator`.
            # So we patch `veritas_ai_agent...callbacks.detect_sum_cells_direction`.

            after_in_table_parallel_callback(ctx)

            assert mock_detect.call_count >= 2

        formulas = ctx.state["reconstructed_formulas"]
        # We expect vertical replication (Col 1 -> Col 2 if numeric)
        # Grid: Col 1 has 10,20. Col 2 has 10,20. So vertical should replicate to Col 2.

        # We expect horizontal replication (Row 1 -> Row 2 if numeric)
        # Grid: Row 1 has 10,10. Row 2 has 20,20. So horizontal should replicate to Row 2.

        f_strs = [f["inferred_formulas"][0]["formula"] for f in formulas]

        # Check vertical replication to Col 2
        # Original: sum_cells((0, 1, 1), (0, 2, 1))
        # Replicated: sum_cells((0, 1, 2), (0, 2, 2))
        vertical_repl = "sum_cells((0, 1, 2), (0, 2, 2))"
        assert any(vertical_repl in s for s in f_strs), (
            f"Missing vertical replication: {f_strs}"
        )

        # Check horizontal replication to Row 2
        # Original: sum_cells((0, 1, 1), (0, 1, 2))
        # Replicated: sum_cells((0, 2, 1), (0, 2, 2))
        horizontal_repl = "sum_cells((0, 2, 1), (0, 2, 2))"
        assert any(horizontal_repl in s for s in f_strs), (
            f"Missing horizontal replication: {f_strs}"
        )

    def test_logs_warning_on_mixed_dimension(self):
        """Should log warning if direction returns None."""
        ctx = MagicMock()
        ctx.state = {
            "extracted_tables": {"tables": [{"table_index": 0, "grid": []}]},
            "logic_reconciliation_formula_inferer_output": {
                "formulas": [
                    {
                        "target_cell": {
                            "table_index": 0,
                            "row_index": 0,
                            "col_index": 0,
                        },
                        "formula": "mixed_bad_formula",
                    }
                ]
            },
        }

        # We need to ensure that the mocked return value is indeed None
        with (
            patch(
                "veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.callbacks.detect_replication_direction",
                return_value=None,
            ) as mock_detect,
            patch(
                "veritas_ai_agent.sub_agents.numeric_validation.sub_agents.in_table_pipeline.callbacks.logger"
            ) as mock_logger,
        ):
            after_in_table_parallel_callback(ctx)

            assert mock_detect.called
            assert mock_logger.warning.called
            args = mock_logger.warning.call_args
            assert "Skipping formula with mixed/unknown dimension" in args[0][0]
