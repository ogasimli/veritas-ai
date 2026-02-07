"""Logic Consistency Reviewer — fans out findings into parallel batches."""

import json
import os
from typing import Any

from google.adk.agents import LlmAgent
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.fan_out import FanOutAgent, FanOutConfig
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from .prompt import get_reviewer_instruction
from .schema import LogicConsistencyReviewerOutput

_FINDINGS_BATCH_SIZE = int(os.environ.get("REVIEWER_FINDINGS_BATCH_SIZE", "3"))


def _prepare_work_items(state: dict[str, Any]) -> list[list[dict]]:
    """Read detector findings from state and chunk into batches."""
    detector_output = state.get("logic_consistency_detector_output", {})
    if hasattr(detector_output, "model_dump"):
        detector_output = detector_output.model_dump()

    findings = detector_output.get("findings", [])
    if not findings:
        return []

    # Chunk findings into batches
    batches = []
    for i in range(0, len(findings), _FINDINGS_BATCH_SIZE):
        batches.append(findings[i : i + _FINDINGS_BATCH_SIZE])
    return batches


def _create_reviewer_agent(index: int, batch: list[dict], output_key: str) -> LlmAgent:
    """Create a reviewer LlmAgent for one batch of findings."""
    return LlmAgent(
        name=f"LogicConsistencyReviewerBatch_{index}",
        model="gemini-3-pro-preview",
        instruction=get_reviewer_instruction(json.dumps(batch, indent=2)),
        output_key=output_key,
        output_schema=LogicConsistencyReviewerOutput,
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


reviewer_agent = FanOutAgent(
    name="LogicConsistencyReviewer",
    config=FanOutConfig(
        prepare_work_items=_prepare_work_items,
        create_agent=_create_reviewer_agent,
        output_key="logic_consistency_reviewer_output",
        results_field="findings",
        empty_message="No detector findings to review.",
    ),
)
