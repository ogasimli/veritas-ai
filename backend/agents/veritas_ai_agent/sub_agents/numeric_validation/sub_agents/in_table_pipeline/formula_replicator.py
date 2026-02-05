"""Formula replication logic for in-table pipeline.

Expands "anchor" formulas (detected for the first numeric column/row)
to all other applicable columns/rows in the table.

Replication strategy
--------------------
Vertical (column-based):
  * Anchor: sum_col(0, 1, 2, 4) for column 1
  * Replicated: sum_col(0, 2, 2, 4), sum_col(0, 3, 2, 4), ... for other numeric columns
  * Target cells shift: (t, r, 1) → (t, r, 2), (t, r, 3), ...

Horizontal (row-based):
  * Anchor: sum_row(0, 1, 1, 3) for row 1
  * Replicated: sum_row(0, 2, 1, 3), sum_row(0, 3, 1, 3), ... for other numeric rows
  * Target cells shift: (t, 1, c) → (t, 2, c), (t, 3, c), ...

Supported formulas
------------------
* sum_col(t, col, r1, r2)           - contiguous vertical sum
* sum_row(t, row, c1, c2)           - contiguous horizontal sum
* sum_cells((t,r1,c1), (t,r2,c2)...) - non-contiguous sum (vertical or horizontal)

Design notes
------------
* Uses regex to parse formula patterns
* Validates numeric columns/rows before replication
* Maintains deduplication via (target_cell, formula) keys
"""

import logging
import re
from typing import Any

from .schema import InferredFormula, TargetCell

logger = logging.getLogger(__name__)

# Regex patterns for parsing formulas
SUM_COL_PATTERN = re.compile(
    r"sum_col\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)"
)
SUM_ROW_PATTERN = re.compile(
    r"sum_row\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)"
)
SUM_CELLS_PATTERN = re.compile(r"sum_cells\s*\((.*)\)")
CELL_REF_PATTERN = re.compile(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")


def replicate_formulas(
    formulas: list[InferredFormula],
    table_grids: dict[int, list[list[Any]]],
    direction: str = "vertical",
) -> list[InferredFormula]:
    """Replicate anchor formulas across appropriate rows/columns.

    direction: "vertical" (replicate across columns) or "horizontal" (replicate across rows).
    Returns list of InferredFormula including originals and replicated copies.
    """
    replicated_results: list[InferredFormula] = []
    seen_keys: set[tuple] = set()

    for item in formulas:
        # Add the original formula first
        target = item.target_cell
        key = ((target.table_index, target.row_index, target.col_index), item.formula)
        if key not in seen_keys:
            replicated_results.append(item)
            seen_keys.add(key)

        # Use explicit direction instead of inferring from formula
        if direction == "vertical":
            new_formulas = _replicate_vertical(item, table_grids)
        elif direction == "horizontal":
            new_formulas = _replicate_horizontal(item, table_grids)
        else:
            new_formulas = []

        for new_item in new_formulas:
            new_target = new_item.target_cell
            key = (
                (new_target.table_index, new_target.row_index, new_target.col_index),
                new_item.formula,
            )
            if key not in seen_keys:
                replicated_results.append(new_item)
                seen_keys.add(key)

    return replicated_results


def _is_vertical_sum_cells(formula: str) -> bool:
    """Check if sum_cells formula has all cells in same column."""
    cells = CELL_REF_PATTERN.findall(formula)
    if not cells or len(cells) < 2:
        return False
    cols = {int(c[2]) for c in cells}
    return len(cols) == 1


def _is_horizontal_sum_cells(formula: str) -> bool:
    """Check if sum_cells formula has all cells in same row."""
    cells = CELL_REF_PATTERN.findall(formula)
    if not cells or len(cells) < 2:
        return False
    rows = {int(c[1]) for c in cells}
    return len(rows) == 1


def detect_sum_cells_direction(formula: str) -> str | None:
    """Detect replication direction from a sum_cells formula's cell layout.

    Returns
    -------
    "vertical"    - all referenced cells share one column  → replicate across columns
    "horizontal"  - all referenced cells share one row     → replicate across rows
    None          - cells span both dimensions; replication is not yet supported
    """
    if _is_vertical_sum_cells(formula):
        return "vertical"
    if _is_horizontal_sum_cells(formula):
        return "horizontal"
    return None


def _replicate_vertical(
    item: InferredFormula, table_grids: dict
) -> list[InferredFormula]:
    """Replicate column-based formulas to other numeric columns."""
    formula = item.formula
    target = item.target_cell

    # Handle sum_col(t, col, r1, r2)
    match = SUM_COL_PATTERN.match(formula)
    if match:
        t_idx, anchor_col, r1, r2 = map(int, match.groups())
        grid = table_grids.get(t_idx)
        if not grid:
            return []

        results = []
        num_cols = len(grid[0]) if grid else 0

        for c in range(anchor_col + 1, num_cols):
            if _is_column_numeric_in_range(grid, c, r1, r2):
                new_formula = f"sum_col({t_idx}, {c}, {r1}, {r2})"
                new_target = TargetCell(
                    table_index=target.table_index,
                    row_index=target.row_index,
                    col_index=c,
                )
                results.append(
                    InferredFormula(
                        target_cell=new_target,
                        formula=new_formula,
                    )
                )
        return results

    # Handle sum_cells for vertical patterns (same column across cells)
    return _replicate_vertical_sum_cells(item, table_grids)


def _replicate_horizontal(
    item: InferredFormula, table_grids: dict
) -> list[InferredFormula]:
    """Replicate row-based formulas to other rows."""
    formula = item.formula
    target = item.target_cell

    # Handle sum_row(t, row, c1, c2)
    match = SUM_ROW_PATTERN.match(formula)
    if match:
        t_idx, anchor_row, c1, c2 = map(int, match.groups())
        grid = table_grids.get(t_idx)
        if not grid:
            return []

        results = []
        num_rows = len(grid)

        for r in range(anchor_row + 1, num_rows):
            if _is_row_numeric_in_range(grid, r, c1, c2):
                new_formula = f"sum_row({t_idx}, {r}, {c1}, {c2})"
                new_target = TargetCell(
                    table_index=target.table_index,
                    row_index=r,
                    col_index=target.col_index,
                )
                results.append(
                    InferredFormula(
                        target_cell=new_target,
                        formula=new_formula,
                    )
                )
        return results

    return _replicate_horizontal_sum_cells(item, table_grids)


def _replicate_vertical_sum_cells(
    item: InferredFormula, table_grids: dict
) -> list[InferredFormula]:
    """Handle sum_cells((t,r1,c), (t,r2,c)...) - all same column."""
    cells = CELL_REF_PATTERN.findall(item.formula)
    if not cells:
        return []

    t_indices = {int(c[0]) for c in cells}
    cols = {int(c[2]) for c in cells}

    if len(t_indices) != 1 or len(cols) != 1:
        return []

    t_idx = next(iter(t_indices))
    anchor_col = next(iter(cols))
    rows = [int(c[1]) for c in cells]
    target = item.target_cell

    grid = table_grids.get(t_idx)
    if not grid:
        return []

    results = []
    num_cols = len(grid[0]) if grid else 0

    for c in range(anchor_col + 1, num_cols):
        if _are_rows_valid_for_col(grid, c, rows):
            parts = [f"({t_idx}, {r}, {c})" for r in rows]
            new_formula = f"sum_cells({', '.join(parts)})"
            new_target = TargetCell(
                table_index=target.table_index,
                row_index=target.row_index,
                col_index=c,
            )
            results.append(InferredFormula(target_cell=new_target, formula=new_formula))

    return results


def _replicate_horizontal_sum_cells(
    item: InferredFormula, table_grids: dict
) -> list[InferredFormula]:
    """Handle sum_cells((t,r,c1), (t,r,c2)...) - all same row."""
    cells = CELL_REF_PATTERN.findall(item.formula)
    if not cells:
        return []

    t_indices = {int(c[0]) for c in cells}
    rows_set = {int(c[1]) for c in cells}

    if len(t_indices) != 1 or len(rows_set) != 1:
        return []

    t_idx = next(iter(t_indices))
    anchor_row = next(iter(rows_set))
    cols = [int(c[2]) for c in cells]
    target = item.target_cell

    grid = table_grids.get(t_idx)
    if not grid:
        return []

    results = []
    num_rows = len(grid)

    for r in range(anchor_row + 1, num_rows):
        if _are_cols_valid_for_row(grid, r, cols):
            parts = [f"({t_idx}, {r}, {c})" for c in cols]
            new_formula = f"sum_cells({', '.join(parts)})"
            new_target = TargetCell(
                table_index=target.table_index,
                row_index=r,
                col_index=target.col_index,
            )
            results.append(InferredFormula(target_cell=new_target, formula=new_formula))

    return results


# --- Helpers ---


def _is_numeric(val: Any) -> bool:
    return isinstance(val, (int, float))


def _is_column_numeric_in_range(grid: list, col: int, r1: int, r2: int) -> bool:
    if not grid or col >= len(grid[0]):
        return False
    for r in range(max(0, r1), min(len(grid), r2 + 1)):
        if _is_numeric(grid[r][col]):
            return True
    return False


def _is_row_numeric_in_range(grid: list, row: int, c1: int, c2: int) -> bool:
    if row >= len(grid):
        return False
    row_data = grid[row]
    for c in range(max(0, c1), min(len(row_data), c2 + 1)):
        if _is_numeric(row_data[c]):
            return True
    return False


def _are_rows_valid_for_col(grid: list, col: int, rows: list[int]) -> bool:
    if not grid or col >= len(grid[0]):
        return False
    for r in rows:
        if r < len(grid) and _is_numeric(grid[r][col]):
            return True
    return False


def _are_cols_valid_for_row(grid: list, row: int, cols: list[int]) -> bool:
    if row >= len(grid):
        return False
    row_data = grid[row]
    for c in cols:
        if c < len(row_data) and _is_numeric(row_data[c]):
            return True
    return False
