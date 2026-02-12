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
* sum_col(t, col, r1, r2)                          - contiguous vertical sum
* sum_row(t, row, c1, c2)                          - contiguous horizontal sum
* sum_cells((t,r1,c1), (t,r2,c2)...)               - non-contiguous sum
* cell(t, r, c)                                    - single cell reference
* cell(t,r,c) + cell(t,r,c) - cell(t,r,c) ...      - compound arithmetic

Design notes
------------
* Uses regex to parse formula patterns
* Validates numeric columns/rows before replication
* Maintains deduplication via (target_cell, formula) keys
* Compound arithmetic formulas (cell() OP cell()) are replicated by
  shifting column/row indices in each cell() reference via re.sub,
  preserving operators and formula structure.
"""

import logging
import re
from typing import Any

from .schema import TargetCell
from .sub_agents.logic_reconciliation_check.sub_agents.fan_out.schema import (
    LogicInferredFormula,
)
from .sub_agents.vertical_horizontal_check.schema import (
    HorizontalVerticalCheckInferredFormula,
)

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
CELL_FUNC_PATTERN = re.compile(r"cell\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")


def _make_formula_item(
    target: TargetCell, formula: str, as_multi: bool
) -> HorizontalVerticalCheckInferredFormula | LogicInferredFormula:
    """Create the appropriate formula item type based on as_multi flag."""
    if as_multi:
        return LogicInferredFormula(target_cell=target, formulas=[formula])
    return HorizontalVerticalCheckInferredFormula(target_cell=target, formula=formula)


def replicate_formulas(
    formulas: list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula],
    table_grids: dict[int, list[list[Any]]],
    direction: str = "vertical",
) -> list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula]:
    """Replicate anchor formulas across appropriate rows/columns.

    Handles both single-formula (InferredFormula) and multi-formula (LogicInferredFormula) inputs.
    Returns list of same type as input, including originals and replicated copies.
    """
    if not formulas:
        return []

    # Detect input type from first item
    is_multi = hasattr(formulas[0], "formulas")
    replicated_results: list[
        HorizontalVerticalCheckInferredFormula | LogicInferredFormula
    ] = []
    seen_keys: set[tuple] = set()

    for item in formulas:
        # Add the original formula first
        target = item.target_cell
        if isinstance(item, LogicInferredFormula):
            f_list = item.formulas
        else:
            f_list = [item.formula]

        # Since we want to return the same type, let's process each formula in the item
        for f_str in f_list:
            key = ((target.table_index, target.row_index, target.col_index), f_str)
            if key not in seen_keys:
                replicated_results.append(_make_formula_item(target, f_str, is_multi))
                seen_keys.add(key)

            # Replicate
            new_items = []
            if direction == "vertical":
                new_items = _replicate_vertical_str(
                    f_str, target, table_grids, is_multi
                )
            elif direction == "horizontal":
                new_items = _replicate_horizontal_str(
                    f_str, target, table_grids, is_multi
                )

            for new_item in new_items:
                if is_multi and isinstance(new_item, LogicInferredFormula):
                    new_f = new_item.formulas[0]
                elif isinstance(new_item, HorizontalVerticalCheckInferredFormula):
                    new_f = new_item.formula
                else:
                    continue
                new_target = new_item.target_cell
                k = (
                    (
                        new_target.table_index,
                        new_target.row_index,
                        new_target.col_index,
                    ),
                    new_f,
                )
                if k not in seen_keys:
                    replicated_results.append(new_item)
                    seen_keys.add(k)

    return replicated_results


def _all_refs_same_column(formula: str) -> bool:
    """Check if all (t, r, c) references in formula share the same column.

    Works for both sum_cells() and compound cell() arithmetic formulas,
    since CELL_REF_PATTERN matches the (t, r, c) triplet inside either
    ``sum_cells((0, 1, 2), ...)`` or ``cell(0, 1, 2) + cell(...)``.

    Requires 2+ refs to be meaningful for direction detection.
    """
    cells = CELL_REF_PATTERN.findall(formula)
    if not cells or len(cells) < 2:
        return False
    cols = {int(c[2]) for c in cells}
    return len(cols) == 1


def _all_refs_same_row(formula: str) -> bool:
    """Check if all (t, r, c) references in formula share the same row.

    Works for both sum_cells() and compound cell() arithmetic formulas,
    since CELL_REF_PATTERN matches the (t, r, c) triplet inside either
    ``sum_cells((0, 1, 2), ...)`` or ``cell(0, 1, 2) + cell(...)``.

    Requires 2+ refs to be meaningful for direction detection.
    """
    cells = CELL_REF_PATTERN.findall(formula)
    if not cells or len(cells) < 2:
        return False
    rows = {int(c[1]) for c in cells}
    return len(rows) == 1


def detect_replication_direction(
    item: HorizontalVerticalCheckInferredFormula | LogicInferredFormula,
) -> str | None:
    """Detect replication direction from formula layout relative to target.

    For multi-formula items, uses the first formula as a representative.
    """
    if isinstance(item, LogicInferredFormula):
        formula = item.formulas[0]
    else:
        formula = item.formula
    target = item.target_cell

    if _all_refs_same_column(formula):
        return "vertical"
    if _all_refs_same_row(formula):
        return "horizontal"

    # Default single cell reference logic checks to vertical replication
    # (checking if the same cell logic applies to other columns)
    match = CELL_FUNC_PATTERN.fullmatch(formula)
    if match:
        # Check alignment relative to target
        _, r_src, c_src = map(int, match.groups())

        # If columns match (Target Col == Source Col), it's a vertical relationship (Row diff)
        # -> Replicate across columns
        if c_src == target.col_index:
            return "vertical"

        # If rows match (Target Row == Source Row), it's a horizontal relationship (Col diff)
        # -> Replicate across rows
        if r_src == target.row_index:
            return "horizontal"

    return None


def _replicate_vertical_str(
    formula: str, target: TargetCell, table_grids: dict, as_multi: bool
) -> list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula]:
    """Replicate column-based formulas to other numeric columns."""
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
                results.append(_make_formula_item(new_target, new_formula, as_multi))
        return results

    # Handle cell(t, r, c) - single cell logic replication
    match = CELL_FUNC_PATTERN.fullmatch(formula)
    if match:
        t_src, r_src, c_src = map(int, match.groups())
        grid = table_grids.get(t_src)
        if not grid:
            return []

        results = []
        num_cols = len(grid[0]) if grid else 0
        anchor_col = target.col_index

        for c in range(anchor_col + 1, num_cols):
            offset = c - anchor_col
            new_src_col = c_src + offset

            if _is_column_numeric_in_range(grid, new_src_col, r_src, r_src):
                new_formula = f"cell({t_src}, {r_src}, {new_src_col})"
                new_target = TargetCell(
                    table_index=target.table_index,
                    row_index=target.row_index,
                    col_index=c,
                )
                results.append(_make_formula_item(new_target, new_formula, as_multi))
        return results

    # Handle sum_cells((t,r,c), ...) for vertical patterns
    if SUM_CELLS_PATTERN.match(formula):
        return _replicate_vertical_sum_cells_str(formula, target, table_grids, as_multi)

    # Handle compound arithmetic: cell(...) + cell(...) - cell(...) etc.
    return _replicate_arithmetic_vertical(formula, target, table_grids, as_multi)


def _replicate_horizontal_str(
    formula: str, target: TargetCell, table_grids: dict, as_multi: bool
) -> list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula]:
    """Replicate row-based formulas to other rows."""
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
                results.append(_make_formula_item(new_target, new_formula, as_multi))
        return results

    # Handle cell(t, r, c) - single cell logic replication
    match = CELL_FUNC_PATTERN.fullmatch(formula)
    if match:
        t_src, r_src, c_src = map(int, match.groups())
        grid = table_grids.get(t_src)
        if not grid:
            return []

        results = []
        num_rows = len(grid)
        anchor_row = target.row_index

        for r in range(anchor_row + 1, num_rows):
            offset = r - anchor_row
            new_src_row = r_src + offset

            if _is_row_numeric_in_range(grid, new_src_row, c_src, c_src):
                new_formula = f"cell({t_src}, {new_src_row}, {c_src})"
                new_target = TargetCell(
                    table_index=target.table_index,
                    row_index=r,
                    col_index=target.col_index,
                )
                results.append(_make_formula_item(new_target, new_formula, as_multi))
        return results

    # Handle sum_cells((t,r,c), ...) for horizontal patterns
    if SUM_CELLS_PATTERN.match(formula):
        return _replicate_horizontal_sum_cells_str(
            formula, target, table_grids, as_multi
        )

    # Handle compound arithmetic: cell(...) + cell(...) - cell(...) etc.
    return _replicate_arithmetic_horizontal(formula, target, table_grids, as_multi)


# --- Compound arithmetic replication ---


def _replicate_arithmetic_vertical(
    formula: str, target: TargetCell, table_grids: dict, as_multi: bool
) -> list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula]:
    """Replicate compound arithmetic formulas across columns.

    Uses re.sub to shift column indices in all cell() references while
    preserving operators (+, -, *, /) and formula structure (parentheses).

    Requirements for replication:
    - Formula must contain 2+ cell() references
    - All cell() refs must share the same column (vertical pattern)
    - At least one shifted cell must land on a numeric value
    """
    refs = list(CELL_FUNC_PATTERN.finditer(formula))
    if len(refs) < 2:
        return []

    # All cell() refs must share the same column
    cols = {int(m.group(3)) for m in refs}
    if len(cols) != 1:
        return []

    anchor_col = target.col_index

    # Determine max columns from referenced table grids
    max_cols = 0
    for m in refs:
        t_idx = int(m.group(1))
        grid = table_grids.get(t_idx)
        if grid and grid[0]:
            max_cols = max(max_cols, len(grid[0]))
    if max_cols == 0:
        return []

    results = []
    for c in range(anchor_col + 1, max_cols):
        offset = c - anchor_col

        # Validate: all shifted refs in bounds, at least one numeric
        valid = True
        any_numeric = False
        for m in refs:
            t_idx = int(m.group(1))
            r = int(m.group(2))
            new_c = int(m.group(3)) + offset
            grid = table_grids.get(t_idx)
            if not grid or new_c >= len(grid[0]):
                valid = False
                break
            if r < len(grid) and _is_numeric(grid[r][new_c]):
                any_numeric = True

        if not valid or not any_numeric:
            continue

        # Shift column index in every cell() reference, preserving everything else
        new_formula = CELL_FUNC_PATTERN.sub(
            lambda m,
            _o=offset: f"cell({m.group(1)}, {m.group(2)}, {int(m.group(3)) + _o})",
            formula,
        )

        new_target = TargetCell(
            table_index=target.table_index,
            row_index=target.row_index,
            col_index=c,
        )
        results.append(_make_formula_item(new_target, new_formula, as_multi))

    return results


def _replicate_arithmetic_horizontal(
    formula: str, target: TargetCell, table_grids: dict, as_multi: bool
) -> list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula]:
    """Replicate compound arithmetic formulas across rows.

    Uses re.sub to shift row indices in all cell() references while
    preserving operators (+, -, *, /) and formula structure (parentheses).

    Requirements for replication:
    - Formula must contain 2+ cell() references
    - All cell() refs must share the same row (horizontal pattern)
    - At least one shifted cell must land on a numeric value
    """
    refs = list(CELL_FUNC_PATTERN.finditer(formula))
    if len(refs) < 2:
        return []

    # All cell() refs must share the same row
    rows = {int(m.group(2)) for m in refs}
    if len(rows) != 1:
        return []

    anchor_row = target.row_index

    # Determine max rows from referenced table grids
    max_rows = 0
    for m in refs:
        t_idx = int(m.group(1))
        grid = table_grids.get(t_idx)
        if grid:
            max_rows = max(max_rows, len(grid))
    if max_rows == 0:
        return []

    results = []
    for r in range(anchor_row + 1, max_rows):
        offset = r - anchor_row

        # Validate: all shifted refs in bounds, at least one numeric
        valid = True
        any_numeric = False
        for m in refs:
            t_idx = int(m.group(1))
            new_r = int(m.group(2)) + offset
            c = int(m.group(3))
            grid = table_grids.get(t_idx)
            if not grid or new_r >= len(grid):
                valid = False
                break
            if c < len(grid[new_r]) and _is_numeric(grid[new_r][c]):
                any_numeric = True

        if not valid or not any_numeric:
            continue

        # Shift row index in every cell() reference, preserving everything else
        new_formula = CELL_FUNC_PATTERN.sub(
            lambda m,
            _o=offset: f"cell({m.group(1)}, {int(m.group(2)) + _o}, {m.group(3)})",
            formula,
        )

        new_target = TargetCell(
            table_index=target.table_index,
            row_index=r,
            col_index=target.col_index,
        )
        results.append(_make_formula_item(new_target, new_formula, as_multi))

    return results


# --- sum_cells replication ---


def _replicate_vertical_sum_cells_str(
    formula: str, target: TargetCell, table_grids: dict, as_multi: bool
) -> list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula]:
    """Handle sum_cells((t,r1,c), (t,r2,c)...) - all same column."""
    cells = CELL_REF_PATTERN.findall(formula)
    if not cells:
        return []

    t_indices = {int(c[0]) for c in cells}
    cols = {int(c[2]) for c in cells}

    if len(t_indices) != 1 or len(cols) != 1:
        return []

    t_idx = next(iter(t_indices))
    anchor_col = next(iter(cols))
    rows = [int(c[1]) for c in cells]

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
            results.append(_make_formula_item(new_target, new_formula, as_multi))

    return results


def _replicate_horizontal_sum_cells_str(
    formula: str, target: TargetCell, table_grids: dict, as_multi: bool
) -> list[HorizontalVerticalCheckInferredFormula | LogicInferredFormula]:
    """Handle sum_cells((t,r,c1), (t,r,c2)...) - all same row."""
    cells = CELL_REF_PATTERN.findall(formula)
    if not cells:
        return []

    t_indices = {int(c[0]) for c in cells}
    rows_set = {int(c[1]) for c in cells}

    if len(t_indices) != 1 or len(rows_set) != 1:
        return []

    t_idx = next(iter(t_indices))
    anchor_row = next(iter(rows_set))
    cols = [int(c[2]) for c in cells]

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
            results.append(_make_formula_item(new_target, new_formula, as_multi))

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
