"""Callbacks for the Table Namer agent.

Pipeline position
-----------------
    before_agent_callback   ->   LlmAgent (names tables)   ->   after_agent_callback
           |                                                            |
    runs programmatic                                         parses LLM JSON,
    extraction, stores                                        merges names into
    raw tables in state                                       raw tables, writes
                                                              state["extracted_tables"]
"""

import json
import logging
from typing import Any

from google.adk.agents.callback_context import CallbackContext

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.sub_agents.in_table_pipeline.grid_utils import (
    add_index_headers,
    strip_empty_rows_and_cols,
)
from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.numeric_validation.table_extraction import (
    extract_tables_from_markdown,
    tables_to_json,
)

from .schema import TableNameAssignment, TableNamerOutput

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Before agent callback
# ---------------------------------------------------------------------------


async def before_agent_callback(callback_context: CallbackContext) -> None:
    """Extract tables programmatically and store them in state.

    Reads:
        document_markdown  - populated by DocumentMarkdownPlugin (app-level)

    Writes:
        extracted_tables_raw  - the raw extraction envelope with table grids
    """
    markdown = callback_context.state.get("document_markdown", "")
    if not markdown:
        logger.warning("No document_markdown in state; table extraction skipped.")
        callback_context.state["extracted_tables_raw"] = tables_to_json([])
        return

    raw_tables = extract_tables_from_markdown(markdown)
    for table in raw_tables:
        table["grid"] = add_index_headers(strip_empty_rows_and_cols(table["grid"]))
    callback_context.state["extracted_tables_raw"] = tables_to_json(raw_tables)
    logger.info("Extracted %d tables; raw data stored.", len(raw_tables))


# ---------------------------------------------------------------------------
# After agent callback
# ---------------------------------------------------------------------------


async def after_agent_callback(callback_context: CallbackContext) -> None:
    """Merge LLM-assigned names with the raw tables.

    Reads:
        extracted_tables_raw  - populated by before_agent_callback
        table_namer_output    - populated by the LlmAgent (output_key)

    Writes:
        extracted_tables      - final envelope with table_index, name, grid
    """
    raw_tables = callback_context.state.get("extracted_tables_raw", {}).get(
        "tables", []
    )

    # --- Parse the LLM output ---
    name_map: dict[int, str] = {}
    namer_output = callback_context.state.get("table_namer_output")

    if namer_output is not None:
        name_map = _parse_namer_output(namer_output)

    if not name_map:
        logger.warning(
            "Table namer produced no usable name assignments; "
            "falling back to default names."
        )

    # --- Merge names with raw tables ---
    merged: list[dict] = []
    for table in raw_tables:
        idx = table["table_index"]
        name = name_map.get(idx, f"Table {idx}")
        merged.append(
            {
                "table_index": idx,
                "table_name": name,
                "grid": table["grid"],
            }
        )

    callback_context.state["extracted_tables"] = {"tables": merged}
    logger.info("Merged names for %d tables into extracted_tables.", len(merged))


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------


def _parse_namer_output(raw: Any) -> dict[int, str]:
    """Extract {table_index -> name} from whatever the LLM wrote to state.

    The output may arrive as:
        - A ``TableNamerOutput`` / dict already validated by ADK's output_schema
        - A raw JSON string (if structured output parsing failed)
        - Something else entirely (returns empty dict -> triggers fallback)
    """
    # 1. Already a validated Pydantic model or a dict with our expected shape
    if isinstance(raw, TableNamerOutput):
        return {a.table_index: a.table_name for a in raw.table_names}

    if isinstance(raw, dict):
        # ADK serialises the output_schema result as a dict
        assignments = raw.get("table_names", [])
        if assignments:
            return _assignments_to_map(assignments)
        # Fallback: maybe the dict IS the raw JSON array the LLM returned
        # (shouldn't normally happen with output_schema, but be defensive)

    # 2. Raw string — try to extract a JSON array
    if isinstance(raw, str):
        return _parse_json_string(raw)

    logger.warning("Unrecognised table_namer_output type: %s", type(raw))
    return {}


def _assignments_to_map(assignments: list) -> dict[int, str]:
    """Convert a list of assignment dicts/objects to {index -> name}."""
    result: dict[int, str] = {}
    for item in assignments:
        if isinstance(item, TableNameAssignment):
            result[item.table_index] = item.table_name
        elif isinstance(item, dict) and "table_index" in item and "table_name" in item:
            result[item["table_index"]] = item["table_name"]
    return result


def _parse_json_string(text: str) -> dict[int, str]:
    """Best-effort parse of a JSON array from a raw LLM string."""
    # Strip common markdown code-fence wrapping
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove first and last lines (fences)
        stripped = "\n".join(lines[1:-1]).strip()

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse JSON from table_namer_output string.")
        return {}

    if not isinstance(data, list):
        logger.warning("Parsed JSON is not a list: %s", type(data))
        return {}

    return _assignments_to_map(data)
