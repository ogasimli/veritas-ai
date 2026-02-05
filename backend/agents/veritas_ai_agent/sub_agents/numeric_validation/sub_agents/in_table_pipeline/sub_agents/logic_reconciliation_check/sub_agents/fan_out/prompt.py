"""Prompts for logic reconciliation fan-out (per-table check)."""

TABLE_INSTRUCTION = """
TODO: Add prompt content for single-table logic reconciliation check.

Context:
{table_data}

Rules:
1. Detect logical relationships (roll-forwards, reconciliations).
2. Use ONLY `sum_cells((t,r,c), (t,r,c), ...)`.
3. Do NOT use `sum_col` or `sum_row`.
4. Do NOT use ranges.
5. Output ONE anchor formula per detected pattern.
"""


def get_table_instruction(table_json: str) -> str:
    """Inject table data into the table instruction."""
    return TABLE_INSTRUCTION.replace("{table_data}", table_json)
