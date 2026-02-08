"""Formula parsing and evaluation for numeric validation.

Grids arriving here have already been parsed by
``table_extraction.number_parser`` — every numeric cell is a plain
``float``.  Non-numeric cells (row / column labels) are ``str``.
This module therefore does *no* string-to-number conversion; it only
evaluates formula expressions against pre-parsed grids.

Supports formulas that span multiple tables.  Every helper function
takes a ``table`` index as its first positional argument.

Formula syntax (all indices are 0-based, ranges inclusive):
    cell(table, row, col)
    sum_row(table, row, start_col, end_col)
    sum_col(table, col, start_row, end_row)
    sum_cells((table, row, col), ...)
    Standard arithmetic: +  -  *  /
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def evaluate_formula_with_tables(
    formula: str, table_grids: dict[int, list[list[Any]]]
) -> float:
    """Evaluate *formula* against a dict of table grids keyed by table_index.

    Cells that are ``int`` or ``float`` are used directly.
    Any other type (label strings, empty strings, None) evaluates to 0.0.
    """

    def _cell_value(table: int, row: int, col: int) -> float:
        try:
            item = table_grids[table][row][col]
            if isinstance(item, (int, float)):
                return float(item)
            return 0.0
        except (IndexError, KeyError, TypeError):
            return 0.0

    def cell(table: int, row: int, col: int) -> float:
        return _cell_value(table, row, col)

    def sum_col(table: int, col: int, start_row: int, end_row: int) -> float:
        return sum(_cell_value(table, r, col) for r in range(start_row, end_row + 1))

    def sum_row(table: int, row: int, start_col: int, end_col: int) -> float:
        return sum(_cell_value(table, row, c) for c in range(start_col, end_col + 1))

    def sum_cells(*coords: tuple[int, int, int]) -> float:
        return sum(_cell_value(t, r, c) for t, r, c in coords)

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
        return float(eval(formula, {"__builtins__": {}}, namespace))
    except Exception as e:
        logger.warning("Formula evaluation failed: %s - %s", formula, e)
        return 0.0
