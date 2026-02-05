"""Utilities for vertical and horizontal check agents."""

import math
from typing import Any


def chunk_tables(tables: list[Any], max_size: int = 15) -> list[list[Any]]:
    """Split tables into evenly distributed batches of at most max_size.

    Args:
        tables: List of tables to split.
        max_size: Maximum number of tables per batch.

    Returns:
        List of batches, where each batch is a list of tables.
    """
    n = len(tables)
    if n == 0:
        return []

    # Calculate number of batches needed
    # e.g., if n=16, max_size=15 -> num_batches=2
    num_batches = math.ceil(n / max_size)

    # Distribute tables evenly across batches
    # divmod(16, 2) -> base_size=8, remainder=0 (8+8)
    # divmod(31, 2) -> base_size=15, remainder=1 (16+15)
    base_size, remainder = divmod(n, num_batches)
    batches = []

    start = 0
    for i in range(num_batches):
        # Add 1 extra item to the first 'remainder' batches to distribute remainder
        size = base_size + (1 if i < remainder else 0)
        batches.append(tables[start : start + size])
        start += size

    return batches
