"""Tools for in-table formula evaluation."""

import logging
import re
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)


def parse_number(value_str: str) -> float:
    """Handle number formats. Expects US format, but robust to common variations."""
    if not value_str or not isinstance(value_str, str) or value_str.strip() == "":
        return 0.0

    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[^\d.,()-]", "", value_str)

    # Handle parentheses as negative: (500) -> -500
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]

    # Remove thousands separators (assumed comma)
    cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def evaluate_single_formula(formula: str, grid: list[list[Any]]) -> float:
    """Evaluate a single formula against a grid.

    Args:
        formula: The formula string to evaluate (e.g., "sum_row(1, 1, 3)")
        grid: The table grid as a list of lists of objects or dicts.
              Each cell expected to have a "value" attribute or key.
    """

    def cell(row: int, col: int) -> float:
        """Get numeric value at (row, col)."""
        try:
            # Handle both dict and object access safely
            item = grid[row][col]
            if isinstance(item, dict):
                val = item.get("value", "")
            else:
                val = getattr(item, "value", "")
            return parse_number(str(val))
        except (IndexError, KeyError, TypeError, AttributeError):
            return 0.0

    def sum_col(col: int, start_row: int, end_row: int) -> float:
        """Sum a column range (inclusive)."""
        return sum(cell(r, col) for r in range(start_row, end_row + 1))

    def sum_row(row: int, start_col: int, end_col: int) -> float:
        """Sum a row range (inclusive)."""
        return sum(cell(row, c) for c in range(start_col, end_col + 1))

    def sum_cells(*coords) -> float:
        """Sum specific cells. Each coord is (row, col) tuple."""
        return sum(cell(r, c) for r, c in coords)

    # Controlled namespace - only these functions available
    namespace = {
        "cell": cell,
        "sum_col": sum_col,
        "sum_row": sum_row,
        "sum_cells": sum_cells,
        "abs": abs,
        "min": min,
        "max": max,
        "round": round,
    }

    try:
        # Evaluate formula safely using restricted eval
        return float(eval(formula, {"__builtins__": {}}, namespace))
    except Exception as e:
        logger.warning(f"Formula evaluation failed: {formula}. Error: {e}")
        return 0.0
