"""Chunking helper for cross-table FSLI analysis."""

import os

# ---------------------------------------------------------------------------
# Environment-configurable chunk size
# ---------------------------------------------------------------------------

FSLI_BATCH_SIZE = int(os.getenv("FSLI_BATCH_SIZE", "5"))


# ---------------------------------------------------------------------------
# Chunking helper (pure function - unit-testable)
# ---------------------------------------------------------------------------


def chunk_fsli_list(fsli_names: list[str], batch_size: int) -> list[list[str]]:
    """Split *fsli_names* into chunks of at most *batch_size*."""
    return [
        fsli_names[i : i + batch_size] for i in range(0, len(fsli_names), batch_size)
    ]
