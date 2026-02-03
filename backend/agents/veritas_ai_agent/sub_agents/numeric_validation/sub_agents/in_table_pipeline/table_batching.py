"""Complexity-based table batching for the in-table fan-out.

Pure functions with no ADK dependencies.  All thresholds are module-level
constants read once from the environment; tests patch them directly on this
module.
"""

import os

SIMPLE_TABLE_THRESHOLD = int(os.getenv("SIMPLE_TABLE_THRESHOLD", "30"))
COMPLEX_TABLE_THRESHOLD = int(os.getenv("COMPLEX_TABLE_THRESHOLD", "100"))
MAX_BATCH_COMPLEXITY = int(os.getenv("MAX_BATCH_COMPLEXITY", "80"))


def calculate_table_complexity(table: dict) -> int:
    """Score a table by size, numeric density, and subtotal-row count."""
    grid = table["grid"]
    rows = len(grid)
    cols = len(grid[0]) if grid else 0
    size_score = rows * cols

    numeric_cells = sum(
        1 for row in grid for cell in row if isinstance(cell, (int, float))
    )
    numeric_ratio = numeric_cells / max(size_score, 1)

    subtotal_keywords = ["total", "subtotal", "net", "gross", "balance", "sum"]
    subtotal_rows = sum(
        1 for row in grid if any(kw in str(row[0]).lower() for kw in subtotal_keywords)
    )

    return int(size_score + (numeric_ratio * 20) + (subtotal_rows * 10))


def batch_tables_by_complexity(tables: list[dict]) -> list[list[dict]]:
    """Group tables into batches respecting complexity thresholds.

    Tables scoring >= COMPLEX_TABLE_THRESHOLD are always alone.
    Remaining tables are packed greedily (descending complexity) until
    adding the next one would exceed MAX_BATCH_COMPLEXITY.
    """
    scored = [(t, calculate_table_complexity(t)) for t in tables]
    scored.sort(key=lambda x: x[1], reverse=True)

    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_complexity = 0

    for table, complexity in scored:
        if complexity >= COMPLEX_TABLE_THRESHOLD:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_complexity = 0
            batches.append([table])
            continue

        if current_complexity + complexity > MAX_BATCH_COMPLEXITY:
            if current_batch:
                batches.append(current_batch)
            current_batch = [table]
            current_complexity = complexity
        else:
            current_batch.append(table)
            current_complexity += complexity

    if current_batch:
        batches.append(current_batch)

    return batches
