"""Callbacks for the Aggregator agent.

Pipeline position
-----------------
    before_agent_callback   ->   LlmAgent (aggregator)
           |                            |
    evaluates every formula     deduplicates findings,
    in reconstructed_formulas,  writes human-readable
    filters & sorts issues,     descriptions, writes
    writes formula_execution_   numeric_validation_output
    issues to state

The ``before_agent_callback`` is the only computation-heavy step in the
whole aggregator module.  Everything it produces is plain Python data
written to ``state["formula_execution_issues"]``; the LLM that follows
only needs to format and deduplicate those results.
"""

import logging

from google.adk.agents.callback_context import CallbackContext

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.formula_engine import (
    evaluate_formula_with_tables,
)

logger = logging.getLogger(__name__)

# A discrepancy smaller than this (in absolute terms) is treated as
# rounding noise and suppressed.
DIFFERENCE_THRESHOLD = 1.0


# ---------------------------------------------------------------------------
# Before-agent callback  (formula execution)
# ---------------------------------------------------------------------------


async def before_agent_callback(callback_context: CallbackContext) -> None:
    """Evaluate all reconstructed formulas and store filtered issues.

    Reads:
        reconstructed_formulas  - list written by the in-table and
                                  cross-table pipelines
        extracted_tables        - envelope with ``tables`` list (grids)

    Writes:
        formula_execution_issues - list of issue dicts sorted by
                                   absolute difference descending
    """
    state = callback_context.state
    formulas: list = state.get("reconstructed_formulas", [])
    tables: list = state.get("extracted_tables", {}).get("tables", [])

    # Build lookup maps keyed by table_index
    table_grids: dict[int, list] = {t["table_index"]: t["grid"] for t in tables}
    table_names: dict[int, str] = {
        t["table_index"]: t.get("table_name", f"Table {t['table_index']}")
        for t in tables
    }

    issues: list[dict] = []
    for entry in formulas:
        check_type = entry.get("check_type")
        if check_type == "in_table":
            issues.extend(_evaluate_in_table(entry, table_grids, table_names))
        elif check_type == "cross_table":
            issues.extend(_evaluate_cross_table(entry, table_grids, table_names))
        else:
            logger.warning("Unknown check_type %r; skipping entry.", check_type)

    # Severity-first ordering - the LLM prompt preserves this order
    issues.sort(key=lambda x: abs(x.get("difference", 0)), reverse=True)
    state["formula_execution_issues"] = issues

    logger.info(
        "Formula execution: %d formulas evaluated → %d issues (threshold %.1f).",
        sum(len(e.get("inferred_formulas", [])) for e in formulas),
        len(issues),
        DIFFERENCE_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Per-check-type evaluators
# ---------------------------------------------------------------------------


def _evaluate_in_table(
    entry: dict,
    table_grids: dict[int, list],
    table_names: dict[int, str],
) -> list[dict]:
    """Evaluate in-table formulas against their target value.

    In-table formulas are *expected-value* expressions (e.g. ``sum_col(…)``).
    A meaningful comparison requires ``actual_value`` to have been populated
    by the upstream pipeline.  Entries where it is ``None`` are skipped - the
    in-table fan-out currently leaves target identification to a future pass.
    """
    actual_value = entry.get("actual_value")
    if actual_value is None:
        return []

    table_index = entry.get("table_index")
    table_name = f"Table {table_index}"
    if isinstance(table_index, int):
        table_name = table_names.get(table_index, table_name)

    issues: list[dict] = []
    for inferred in entry.get("inferred_formulas", []):
        formula = _extract_formula_string(inferred)
        if not formula:
            continue

        calculated = evaluate_formula_with_tables(formula, table_grids)
        difference = calculated - actual_value

        if abs(difference) >= DIFFERENCE_THRESHOLD:
            issues.append(
                {
                    "check_type": "in_table",
                    "table_index": table_index,
                    "table_name": table_name,
                    "formula": formula,
                    "calculated_value": calculated,
                    "actual_value": actual_value,
                    "difference": difference,
                }
            )

    return issues


def _evaluate_cross_table(
    entry: dict,
    table_grids: dict[int, list],
    table_names: dict[int, str],
) -> list[dict]:
    """Evaluate cross-table formulas.

    Cross-table formulas are *difference* expressions designed to evaluate
    to 0 when the underlying relationship holds
    (e.g. ``cell(0, 5, 1) - cell(2, 20, 1)``).  A non-zero result IS the
    discrepancy - ``actual_value`` is implicitly 0.
    """
    issues: list[dict] = []
    for inferred in entry.get("inferred_formulas", []):
        formula = _extract_formula_string(inferred)
        if not formula:
            continue

        difference = evaluate_formula_with_tables(formula, table_grids)

        if abs(difference) >= DIFFERENCE_THRESHOLD:
            issues.append(
                {
                    "check_type": "cross_table",
                    "formula": formula,
                    "calculated_value": difference,
                    "actual_value": 0.0,
                    "difference": difference,
                }
            )

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_formula_string(inferred: object) -> str | None:
    """Pull the formula string out of whatever shape arrived in state.

    Handles three cases that occur in practice:
        - ``{"formula": "<string>"}``           - normal path
        - A Pydantic model with a ``.formula`` attribute
        - A bare string                         - defensive fallback
    """
    if isinstance(inferred, str):
        return inferred
    if isinstance(inferred, dict):
        val = inferred.get("formula")
        return val if isinstance(val, str) else None
    if hasattr(inferred, "formula"):
        return inferred.formula
    return None
