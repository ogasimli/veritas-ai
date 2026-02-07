"""CrossTableFormulaFanOut — fans out FSLI chunks into parallel LlmAgents.

Migrated to use the generic ``FanOutAgent`` pattern.

Design notes
------------
* FSLI list = ``primary_fsli`` + ``sub_fsli`` from
  ``state["fsli_extractor_output"]``.
* Chunk size is controlled by the ``FSLI_BATCH_SIZE`` env var (default 5).
* Each sub-agent writes to a deterministic output key managed by FanOutAgent.
* Chunks are processed sequentially (``batch_size=1``) for rate limiting.
* Custom aggregation stamps ``check_type="cross_table"`` on every formula dict
  and writes to ``state["cross_table_fan_out_output"]``.
* An ``after_agent_callback`` copies formulas into the shared
  ``state["reconstructed_formulas"]`` list.
"""

import json
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.fan_out import FanOutAgent, FanOutConfig
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from .callbacks import after_fan_out_callback
from .chunking import FSLI_BATCH_SIZE, chunk_fsli_list
from .prompt import get_batch_instruction
from .schema import CrossTableBatchOutput

# ---------------------------------------------------------------------------
# FanOutAgent callbacks
# ---------------------------------------------------------------------------


def _prepare_work_items(state: dict[str, Any]) -> list[tuple[str, str]]:
    """Read FSLIs and tables from state, return chunked work items.

    Each work item is a ``(fsli_batch_json, tables_json)`` tuple so that
    ``_create_chunk_agent`` has everything it needs.
    """
    extractor_output = state.get("fsli_extractor_output", {})
    if hasattr(extractor_output, "model_dump"):
        extractor_output = extractor_output.model_dump()

    primary = extractor_output.get("primary_fsli", [])
    sub = extractor_output.get("sub_fsli", [])
    all_fslis = primary + sub

    if not all_fslis:
        return []

    extracted_tables = state.get("extracted_tables", {})
    tables_json = json.dumps(extracted_tables)

    chunks = chunk_fsli_list(all_fslis, FSLI_BATCH_SIZE)
    return [(json.dumps(chunk), tables_json) for chunk in chunks]


def _create_chunk_agent(index: int, work_item: Any, output_key: str) -> LlmAgent:
    """Return a fresh LlmAgent for one FSLI chunk."""
    fsli_batch_json, tables_json = work_item
    return LlmAgent(
        name=f"cross_table_batch_{index}",
        model="gemini-3-pro-preview",
        instruction=get_batch_instruction(fsli_batch_json, tables_json),
        output_key=output_key,
        output_schema=CrossTableBatchOutput,
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


def _aggregate(outputs: list[dict]) -> dict[str, list[dict]]:
    """Stamp ``check_type="cross_table"`` on each formula dict.

    Parameters
    ----------
    outputs : list[dict]
        List of normalised ``CrossTableBatchOutput`` dicts, each containing
        a ``"formulas"`` key with a list of ``CrossTableFormula`` dicts.

    Returns
    -------
    dict
        ``{"formulas": [<all transformed formula dicts>]}``.
    """
    all_formulas: list[dict] = []
    for output in outputs:
        for formula in output.get("formulas", []):
            formula["check_type"] = "cross_table"
            all_formulas.append(formula)
    return {"formulas": all_formulas}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

cross_table_fan_out_agent = FanOutAgent(
    name="CrossTableFormulaFanOut",
    config=FanOutConfig(
        prepare_work_items=_prepare_work_items,
        create_agent=_create_chunk_agent,
        output_key="cross_table_fan_out_output",
        results_field="formulas",
        batch_size=1,
        aggregate=_aggregate,
        empty_message="No FSLIs to analyse; skipping.",
    ),
    after_agent_callback=after_fan_out_callback,
)
