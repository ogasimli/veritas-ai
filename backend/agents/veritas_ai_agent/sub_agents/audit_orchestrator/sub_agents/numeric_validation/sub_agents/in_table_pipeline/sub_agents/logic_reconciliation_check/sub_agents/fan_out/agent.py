"""Logic Reconciliation Check Fan-Out Agent — fans out per candidate table."""

import json
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.fan_out import FanOutAgent, FanOutConfig
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_config import GEMINI_PRO

from .prompt import get_table_instruction
from .schema import LogicCheckAgentOutput


def _prepare_work_items(state: dict[str, Any]) -> list[dict]:
    """Read screener output and return candidate tables for fan-out."""
    screener_output = state.get("logic_reconciliation_check_screener_output", {})
    if hasattr(screener_output, "model_dump"):
        screener_output = screener_output.model_dump()

    candidates = screener_output.get("candidate_table_indexes", [])

    all_tables_json = state.get("extracted_tables", "[]")
    if isinstance(all_tables_json, str):
        try:
            all_tables = json.loads(all_tables_json)
        except json.JSONDecodeError:
            all_tables = []
    else:
        all_tables = all_tables_json

    # Support if all_tables is a dict with "tables" key or just a list
    tables_list = (
        all_tables if isinstance(all_tables, list) else all_tables.get("tables", [])
    )

    candidate_tables = []
    for idx in candidates:
        matching_table = next(
            (t for t in tables_list if t.get("table_index") == idx), None
        )
        if matching_table:
            candidate_tables.append(matching_table)

    return candidate_tables


def _create_table_agent(index: int, work_item: Any, output_key: str) -> LlmAgent:
    """Create a check agent for a specific candidate table."""
    table_envelope = json.dumps({"tables": [work_item]})
    return LlmAgent(
        name=f"LogicReconciliationFormulaInfererTableAgent_{index}",
        model=GEMINI_PRO,
        instruction=get_table_instruction(table_envelope),
        output_schema=LogicCheckAgentOutput,
        output_key=output_key,
        on_model_error_callback=default_model_error_handler,
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False, thinking_level="high"
            )
        ),
        generate_content_config=types.GenerateContentConfig(
            http_options=types.HttpOptions(retry_options=get_default_retry_config())
        ),
    )


logic_reconciliation_formula_inferer = FanOutAgent(
    name="LogicReconciliationFormulaInferer",
    config=FanOutConfig(
        prepare_work_items=_prepare_work_items,
        create_agent=_create_table_agent,
        output_key="logic_reconciliation_formula_inferer_output",
        results_field="formulas",
        empty_message="No candidate tables for logic reconciliation.",
    ),
)
