"""Post-processing callback for in-table pipeline.

Callback responsibilities
--------------------------
1. Collect outputs from VerticalCheckAgent and HorizontalCheckAgent (vertical_check_output, horizontal_check_output)
2. Replicate anchor formulas across applicable columns/rows using formula_replicator
3. Look up actual_value for each target_cell from table grids
4. Write complete entries to state["reconstructed_formulas"]

State keys read
---------------
* vertical_check_output   - vertical check formulas
* horizontal_check_output  - horizontal check formulas
* extracted_tables             - table grids for actual_value lookup

State keys written
------------------
* reconstructed_formulas - list of dicts with:
    - check_type: "in_table"
    - table_index: int
    - target_cells: list of [table, row, col]
    - actual_value: float | None
    - inferred_formulas: list of {"formula": str}
"""

import logging

from google.adk.agents.callback_context import CallbackContext

from .formula_replicator import detect_replication_direction, replicate_formulas
from .schema import InferredFormula

logger = logging.getLogger(__name__)


# Keys whose replication direction is determined statically
_FIXED_DIRECTION_KEYS: dict[str, str] = {
    "vertical_check_output": "vertical",
    "horizontal_check_output": "horizontal",
}

# Keys whose replication direction is detected per-formula at runtime
_DYNAMIC_DIRECTION_KEYS: list[str] = [
    "logic_reconciliation_formula_inferer_output",
]


def after_in_table_parallel_callback(callback_context: CallbackContext) -> None:
    """Collect sub-agent outputs, replicate formulas, populate actual_value."""
    state = callback_context.state
    # Robustly handle extracted_tables format
    extracted = state.get("extracted_tables", {})
    if isinstance(extracted, str):
        try:
            import json

            extracted = json.loads(extracted)
        except json.JSONDecodeError:
            extracted = {}

    tables = extracted if isinstance(extracted, list) else extracted.get("tables", [])

    if not tables:
        state.setdefault("reconstructed_formulas", [])
        return

    # 1 & 2. Collect raw formulas and replicate them
    all_replicated: list[InferredFormula] = []
    # Make sure we use a dict for fast lookup
    table_grids = {t.get("table_index"): t.get("grid") for t in tables}

    # Iterate over both fixed and dynamic keys
    all_keys = list(_FIXED_DIRECTION_KEYS.keys()) + _DYNAMIC_DIRECTION_KEYS

    for key in all_keys:
        output = state.get(key)
        if not output:
            continue
        if hasattr(output, "model_dump"):
            output = output.model_dump()

        batch_formulas: list[InferredFormula] = []
        for item in output.get("formulas", []):
            if hasattr(item, "model_dump"):
                item = item.model_dump()

            try:
                # Handle case where item might be just a string if something went wrong, but assume dict
                if isinstance(item, dict):
                    formula = InferredFormula(
                        target_cell=item["target_cell"],
                        formula=item["formula"],
                    )
                    batch_formulas.append(formula)
            except (KeyError, TypeError):
                pass

        if batch_formulas:
            if key in _FIXED_DIRECTION_KEYS:
                # Existing path: single direction for the whole batch
                all_replicated.extend(
                    replicate_formulas(
                        batch_formulas,
                        table_grids,
                        direction=_FIXED_DIRECTION_KEYS[key],
                    )
                )
            else:
                # Dynamic path: detect direction per formula from sum_cells cell layout
                for formula in batch_formulas:
                    direction = detect_replication_direction(formula)
                    if direction is None:
                        logger.warning(
                            "Skipping formula with mixed-dimension cells: %s",
                            formula.formula,
                        )
                        # TODO: Handle formulas where cells span both row and column
                        # dimensions. For now these are skipped.
                        continue
                    all_replicated.extend(
                        replicate_formulas([formula], table_grids, direction=direction)
                    )

    replicated = all_replicated
    # 3. Look up actual values and write to shared state
    state.setdefault("reconstructed_formulas", [])

    for item in replicated:
        target = item.target_cell
        t_idx = target.table_index
        row = target.row_index
        col = target.col_index

        actual_value = None
        try:
            cell_val = table_grids[t_idx][row][col]
            if isinstance(cell_val, (int, float)):
                actual_value = float(cell_val)
            else:
                # Non-numeric / labels / dashes treated as 0.0
                actual_value = 0.0
        except (KeyError, IndexError):
            logger.error(
                "Target cell [%d, %d] is out of bounds for table %r",
                row,
                col,
                t_idx,
            )
        except Exception as e:
            logger.error(
                "Unexpected error looking up target cell [%d, %d] in table %r: %s",
                row,
                col,
                t_idx,
                e,
            )
        state["reconstructed_formulas"].append(
            {
                "check_type": "in_table",
                "table_index": t_idx,
                "target_cells": [
                    {
                        "table_index": t_idx,
                        "row_index": row,
                        "col_index": col,
                    }
                ],
                "actual_value": actual_value,
                "inferred_formulas": [{"formula": item.formula}],
            }
        )
