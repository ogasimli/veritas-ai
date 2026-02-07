"""Agent factory for batched vertical and horizontal check agents.

Architecture
------------
Instead of a single LlmAgent per check type, checks are orchestrated by a
``FanOutAgent``. This agent:
1.  **Splits input tables** into chunks (max 15 tables) to fit within context windows.
2.  **Fans out** parallel ephemeral sub-agents for each batch.
3.  **Aggregates** results from all batches into a unified output.

Factory Functions
-----------------
*   ``create_vertical_check_agent()``: Returns a ``FanOutAgent`` configured with ``VERTICAL_INSTRUCTION``.
*   ``create_horizontal_check_agent()``: Returns a ``FanOutAgent`` configured with ``HORIZONTAL_INSTRUCTION``.

Agent Responsibilities
----------------------
Vertical Logic Auditor (VerticalCheckAgent):
*   Detects column-based formulas.
*   Outputs formulas for the LEFT-MOST numeric column (anchor cell strategy).

Horizontal Logic Auditor (HorizontalCheckAgent):
*   Detects row-based formulas.
*   Outputs formulas for the TOP-MOST numeric row (anchor cell strategy).

Design Notes
------------
*   **Batching**: Even distribution strategy (e.g., 16 tables -> 2 batches of 8) ensures balanced load.
*   **Vectorization**: Prompts enforce "anchor only" rule to minimize output tokens.
*   **Replication**: Python-side replication handles expanding anchor formulas to all rows/cols.
"""

import json
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.fan_out import FanOutAgent, FanOutConfig
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from .prompt import HORIZONTAL_INSTRUCTION, VERTICAL_INSTRUCTION
from .schema import HorizontalVerticalCheckAgentOutput
from .utils import chunk_tables


def _prepare_work_items(state: dict[str, Any]) -> list[list[dict]]:
    """Read extracted tables from state, normalize, and chunk into batches."""
    extracted_tables_json = state.get("extracted_tables", "[]")
    if isinstance(extracted_tables_json, str):
        try:
            extracted_tables_data = json.loads(extracted_tables_json)
        except json.JSONDecodeError:
            extracted_tables_data = []
    else:
        extracted_tables_data = extracted_tables_json

    # Normalization: handle list vs dict envelope
    if isinstance(extracted_tables_data, dict):
        tables = extracted_tables_data.get("tables", [])
    else:
        tables = extracted_tables_data

    if not tables:
        return []

    return chunk_tables(tables, max_size=15)


def _create_check_fan_out_agent(
    name: str, instruction_template: str, output_key: str
) -> FanOutAgent:
    """Internal factory that builds a FanOutAgent for vertical or horizontal checks.

    Parameters
    ----------
    name : str
        Agent name (e.g. ``"VerticalCheckAgent"``).
    instruction_template : str
        Prompt template containing ``{extracted_tables}`` placeholder.
    output_key : str
        State key for the final aggregated result.
    """

    def _create_agent(index: int, work_item: list[dict], output_key: str) -> LlmAgent:
        """Create an LlmAgent for one batch of tables."""
        batch_json = json.dumps({"tables": work_item}, indent=2)
        # Note: Using .replace() instead of .format() because the instruction
        # template contains curly braces for JSON examples which conflict with .format().
        batch_instruction = instruction_template.replace(
            "{extracted_tables}", batch_json
        )

        return LlmAgent(
            name=f"{name}_{index}",
            model="gemini-3-pro-preview",
            instruction=batch_instruction,
            output_schema=HorizontalVerticalCheckAgentOutput,
            output_key=output_key,
            on_model_error_callback=default_model_error_handler,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False, thinking_level="high"
                )
            ),
            generate_content_config=types.GenerateContentConfig(
                http_options=types.HttpOptions(
                    retry_options=get_default_retry_config()
                )
            ),
        )

    return FanOutAgent(
        name=name,
        config=FanOutConfig(
            prepare_work_items=_prepare_work_items,
            create_agent=_create_agent,
            output_key=output_key,
            results_field="formulas",
            batch_size=None,
        ),
    )


def create_vertical_check_agent() -> FanOutAgent:
    """Create the vertical check agent (batched)."""
    return _create_check_fan_out_agent(
        "VerticalCheckAgent", VERTICAL_INSTRUCTION, "vertical_check_output"
    )


def create_horizontal_check_agent() -> FanOutAgent:
    """Create the horizontal check agent (batched)."""
    return _create_check_fan_out_agent(
        "HorizontalCheckAgent", HORIZONTAL_INSTRUCTION, "horizontal_check_output"
    )
