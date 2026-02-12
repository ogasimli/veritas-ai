"""Grid utilities for LLM consumption."""


def strip_empty_rows_and_cols(grid: list[list]) -> list[list]:
    """Strip rows/columns where every cell is an empty string."""
    if not grid:
        return []

    # Strip empty rows
    non_empty_rows = [row for row in grid if not all(cell == "" for cell in row)]
    if not non_empty_rows:
        return []

    # Find non-empty column indices
    num_cols = max(len(row) for row in non_empty_rows)
    non_empty_col_indices = []
    for col_idx in range(num_cols):
        for row in non_empty_rows:
            if col_idx < len(row) and row[col_idx] != "":
                non_empty_col_indices.append(col_idx)
                break

    if not non_empty_col_indices:
        return []

    # Rebuild grid with only non-empty columns
    return [
        [row[c] if c < len(row) else "" for c in non_empty_col_indices]
        for row in non_empty_rows
    ]


def add_index_headers(grid: list[list]) -> list[list]:
    """Prepend a column-index row (row 0) and row-index column (col 0).

    Index values are strings matching actual grid positions after insertion.
    """
    if not grid:
        return grid

    num_cols = max(len(row) for row in grid)

    # Column index row: ["", "1", "2", ..., "num_cols"]
    col_index_row = [""] + [str(c + 1) for c in range(num_cols)]

    # Prepend row index to each data row
    result = [col_index_row]
    for i, row in enumerate(grid):
        result.append([str(i + 1), *row])

    return result
