"""Utilities for vertical and horizontal check agents."""

import math
from typing import Any


def _grid_cell_count(table: Any) -> int:
    """Return the total number of cells in a table's grid.

    Uses ``sum(len(row) for row in grid)`` when the table is a dict with a
    non-empty ``"grid"`` key.  Returns ``1`` otherwise so that gridless tables
    are never treated as zero-weight.
    """
    if not isinstance(table, dict):
        return 1
    grid = table.get("grid")
    if not grid or not isinstance(grid, list):
        return 1
    return sum(len(row) for row in grid if isinstance(row, (list, tuple))) or 1


def chunk_tables(tables: list[Any], max_size: int = 15) -> list[list[Any]]:
    """Split tables into load-balanced batches of at most *max_size*.

    Uses the **LPT (Longest Processing Time) greedy** algorithm: tables are
    sorted by descending grid cell count then each table is assigned to the
    batch with the lowest current total weight.  After assignment, each batch
    is re-sorted by the table's original position so that document order is
    preserved within every batch.

    Args:
        tables: List of tables to split.
        max_size: Maximum number of tables per batch.

    Returns:
        List of batches, where each batch is a list of tables.
    """
    n = len(tables)
    if n == 0:
        return []

    num_batches = math.ceil(n / max_size)

    # Each element is (original_index, table, weight).
    indexed = [(i, t, _grid_cell_count(t)) for i, t in enumerate(tables)]

    # Sort descending by weight for LPT assignment.
    indexed.sort(key=lambda x: x[2], reverse=True)

    # batch_items[b] collects (original_index, table) pairs.
    batch_items: list[list[tuple[int, Any]]] = [[] for _ in range(num_batches)]
    batch_weights: list[int] = [0] * num_batches

    for orig_idx, table, weight in indexed:
        # Pick the lightest batch that still has room.  The tuple key ensures
        # full batches (True > False) sort after non-full ones.
        min_idx = min(
            range(num_batches),
            key=lambda b: (len(batch_items[b]) >= max_size, batch_weights[b]),
        )
        batch_items[min_idx].append((orig_idx, table))
        batch_weights[min_idx] += weight

    # Re-sort each batch by original index to preserve document order.
    batches: list[list[Any]] = []
    for items in batch_items:
        items.sort(key=lambda x: x[0])
        batches.append([table for _, table in items])

    return batches
