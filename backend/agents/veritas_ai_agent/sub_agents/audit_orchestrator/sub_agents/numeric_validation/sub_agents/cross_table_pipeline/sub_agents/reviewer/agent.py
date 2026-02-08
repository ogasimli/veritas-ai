"""Cross-Table Reviewer — fans out findings into parallel batches."""

import json
import os
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.callbacks import strip_injected_context
from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.fan_out import FanOutAgent, FanOutConfig
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from .prompt import get_reviewer_instruction
from .schema import CrossTableReviewerOutput

_FINDINGS_BATCH_SIZE = int(
    os.environ.get("CROSS_TABLE_REVIEWER_BATCH_SIZE", "5")
)

_DETECTOR_OUTPUT_KEYS = [
    "balance_sheet_cross_table_inconsistency_detector_output",
    "income_statement_cross_table_inconsistency_detector_output",
    "cash_flow_cross_table_inconsistency_detector_output",
]


def _prepare_work_items(state: dict[str, Any]) -> list[list[dict]]:
    """Read findings from all 3 detector outputs and chunk into batches."""
    all_findings: list[dict] = []

    for key in _DETECTOR_OUTPUT_KEYS:
        detector_output = state.get(key, {})
        if hasattr(detector_output, "model_dump"):
            detector_output = detector_output.model_dump()
        findings = detector_output.get("findings", [])
        all_findings.extend(findings)

    if not all_findings:
        return []

    batches = []
    for i in range(0, len(all_findings), _FINDINGS_BATCH_SIZE):
        batches.append(all_findings[i : i + _FINDINGS_BATCH_SIZE])
    return batches


def _create_reviewer_agent(
    index: int, batch: list[dict], output_key: str
) -> LlmAgent:
    """Create a reviewer LlmAgent for one batch of findings."""
    return LlmAgent(
        name=f"CrossTableReviewerBatch_{index}",
        model="gemini-3-pro-preview",
        instruction=get_reviewer_instruction(json.dumps(batch, indent=2)),
        include_contents="none",
        output_key=output_key,
        output_schema=CrossTableReviewerOutput,
        on_model_error_callback=default_model_error_handler,
        before_model_callback=strip_injected_context,
        code_executor=BuiltInCodeExecutor(),
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


reviewer_agent = FanOutAgent(
    name="CrossTableReviewer",
    config=FanOutConfig(
        prepare_work_items=_prepare_work_items,
        create_agent=_create_reviewer_agent,
        output_key="cross_table_reviewer_output",
        results_field="findings",
        batch_size=3,
        empty_message="No cross-table findings to review.",
    ),
)
