"""Tests for grid_utils: strip_empty_rows_and_cols and add_index_headers."""

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.grid_utils import (
    add_index_headers,
    strip_empty_rows_and_cols,
)

# ---------------------------------------------------------------------------
# strip_empty_rows_and_cols
# ---------------------------------------------------------------------------


def test_strip_empty_rows():
    """Empty rows are stripped; non-empty rows are kept."""
    grid = [
        ["Header", "Col1"],
        ["", ""],
        ["Assets", "100"],
        ["", ""],
        ["", ""],
        ["Total", "100"],
    ]
    result = strip_empty_rows_and_cols(grid)
    assert result == [
        ["Header", "Col1"],
        ["Assets", "100"],
        ["Total", "100"],
    ]


def test_strip_empty_cols():
    """Empty columns are stripped; non-empty columns are kept."""
    grid = [
        ["Header", "", "Col1"],
        ["Assets", "", "100"],
        ["Total", "", "100"],
    ]
    result = strip_empty_rows_and_cols(grid)
    assert result == [
        ["Header", "Col1"],
        ["Assets", "100"],
        ["Total", "100"],
    ]


def test_strip_mixed_empty_rows_and_cols():
    """Both empty rows and empty columns are stripped."""
    grid = [
        ["Header", "", "Col1"],
        ["", "", ""],
        ["Assets", "", "100"],
    ]
    result = strip_empty_rows_and_cols(grid)
    assert result == [
        ["Header", "Col1"],
        ["Assets", "100"],
    ]


def test_dash_and_zero_not_empty():
    """Rows/cols with '-', 0, or 0.0 are NOT considered empty (only '' is empty)."""
    grid = [
        ["Label", "-"],
        ["Item", 0],
        ["Other", 0.0],
    ]
    result = strip_empty_rows_and_cols(grid)
    assert result == grid


def test_strip_empty_grid():
    """Empty grid returns empty list."""
    assert strip_empty_rows_and_cols([]) == []


def test_strip_all_empty_grid():
    """Grid where all cells are empty returns empty list."""
    grid = [["", ""], ["", ""]]
    assert strip_empty_rows_and_cols(grid) == []


def test_strip_no_empty_rows_or_cols():
    """Grid with no empty rows/cols is returned unchanged."""
    grid = [
        ["H1", "H2"],
        ["R1", "10"],
        ["R2", "20"],
    ]
    result = strip_empty_rows_and_cols(grid)
    assert result == grid


def test_strip_single_cell_grid():
    """Single-cell grid with content is returned unchanged."""
    grid = [["only"]]
    result = strip_empty_rows_and_cols(grid)
    assert result == [["only"]]


# ---------------------------------------------------------------------------
# Composed pipeline: strip_empty_rows_and_cols + add_index_headers
# ---------------------------------------------------------------------------


def test_composed_strip_then_index():
    """Verify the full pipeline: strip empties, then add index headers."""
    grid = [
        ["Header", "", "Col1"],
        ["", "", ""],
        ["Assets", "", 100.0],
        ["Total", "", 100.0],
    ]
    result = add_index_headers(strip_empty_rows_and_cols(grid))
    assert result == [
        ["", "1", "2"],
        ["1", "Header", "Col1"],
        ["2", "Assets", 100.0],
        ["3", "Total", 100.0],
    ]
    # LLM reads "Assets" at r=2, c=1 → grid[2][1] == "Assets"
    assert result[2][1] == "Assets"
    # LLM reads 100.0 at r=2, c=2 → grid[2][2] == 100.0
    assert result[2][2] == 100.0


# ---------------------------------------------------------------------------
# add_index_headers
# ---------------------------------------------------------------------------


def test_add_index_headers_basic():
    """Adds row 0 with column indices and col 0 with row indices."""
    grid = [
        ["Header", "Col1", "Col2"],
        ["Assets", 100.0, 200.0],
        ["Total", 100.0, 200.0],
    ]
    result = add_index_headers(grid)
    assert result == [
        ["", "1", "2", "3"],
        ["1", "Header", "Col1", "Col2"],
        ["2", "Assets", 100.0, 200.0],
        ["3", "Total", 100.0, 200.0],
    ]


def test_add_index_headers_corner_cell():
    """Corner cell [0][0] is empty string."""
    grid = [["A"]]
    result = add_index_headers(grid)
    assert result[0][0] == ""


def test_add_index_headers_positions():
    """Index values match actual grid positions (1-indexed for data)."""
    grid = [
        ["Header", "Col1"],
        ["Assets", 100.0],
    ]
    result = add_index_headers(grid)
    # Column indices in row 0
    assert result[0] == ["", "1", "2"]
    # Row indices in col 0
    assert result[1][0] == "1"
    assert result[2][0] == "2"
    # Data accessible at the position indicated by indices
    assert result[1][1] == "Header"
    assert result[2][2] == 100.0


def test_add_index_headers_empty_grid():
    """Empty grid is returned unchanged."""
    assert add_index_headers([]) == []


def test_add_index_headers_preserves_numeric_types():
    """Numeric values in data are preserved, not converted to strings."""
    grid = [[42, 3.14, "text"]]
    result = add_index_headers(grid)
    assert result[1][1] == 42
    assert result[1][2] == 3.14
    assert result[1][3] == "text"
    # Only index values are strings
    assert isinstance(result[0][1], str)
    assert isinstance(result[1][0], str)


def test_add_index_headers_single_cell():
    """Single-cell grid gets index headers."""
    grid = [["only"]]
    result = add_index_headers(grid)
    assert result == [["", "1"], ["1", "only"]]
