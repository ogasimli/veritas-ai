"""Disclosure Verifier — fans out per applicable standard using FanOutAgent."""

import logging
import re
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.fan_out import FanOutAgent, FanOutConfig
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from ...tools.checklist_loader import load_standard_checklist
from .prompt import get_verifier_instruction
from .schema import DisclosureVerifierOutput

logger = logging.getLogger(__name__)


def _prepare_work_items(state: dict[str, Any]) -> list[tuple[str, dict]]:
    """Read applicable standards from state, load checklists, skip missing ones.

    Returns list of (standard_code, checklist) tuples for standards with valid
    checklists.  Standards whose checklist cannot be loaded are silently skipped
    with a ``logger.warning``.
    """
    scanner_output = state.get("disclosure_scanner_output", {})
    if hasattr(scanner_output, "model_dump"):
        scanner_output = scanner_output.model_dump()

    applicable_standards = scanner_output.get("applicable_standards", [])
    if not applicable_standards:
        return []

    work_items: list[tuple[str, dict]] = []
    for standard_code in applicable_standards:
        try:
            checklist = load_standard_checklist(standard_code)
            work_items.append((standard_code, checklist))
        except ValueError as e:
            logger.warning("Skipping %s: %s", standard_code, e)

    return work_items


def _create_verifier_agent(
    index: int, work_item: tuple[str, dict], output_key: str
) -> LlmAgent:
    """Create a verifier LlmAgent for one applicable standard."""
    standard_code, checklist = work_item
    sanitized_code = re.sub(r"[^a-zA-Z0-9_]", "_", standard_code)
    return create_disclosure_verifier_agent(
        name=f"verify_{sanitized_code}",
        standard_code=standard_code,
        checklist=checklist,
        output_key=output_key,
    )


def create_disclosure_verifier_agent(
    name: str, standard_code: str, checklist: dict, output_key: str
) -> LlmAgent:
    """Factory to create a fresh disclosure verifier for a specific standard.

    Must create new instances each time (ADK single-parent rule).

    Args:
        name: Agent name
        standard_code: IFRS/IAS standard code (e.g., "IAS 1")
        checklist: Loaded checklist data for the standard
        output_key: Session state key for output
    """
    # Build checklist text
    checklist_text = f"## Disclosure Checklist for {standard_code}\n\n"
    checklist_text += f"Standard: {checklist['name']}\n\n"
    checklist_text += "Required disclosures to check:\n\n"

    for disclosure in checklist["disclosures"]:
        ref = disclosure.get("reference", "")
        req = disclosure.get("requirement", "")
        checklist_text += f"- **{disclosure['id']}**: {ref}: {req}\n\n"

    # Inject checklist into instruction placeholder
    full_instruction = get_verifier_instruction(standard_code).replace(
        "{disclosure_checklist}", checklist_text
    )

    return LlmAgent(
        name=name,
        model="gemini-3-pro-preview",
        instruction=full_instruction,
        output_key=output_key,
        output_schema=DisclosureVerifierOutput,
        generate_content_config=types.GenerateContentConfig(
            http_options=types.HttpOptions(retry_options=get_default_retry_config())
        ),
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=False, thinking_level="high"
            )
        ),
        on_model_error_callback=default_model_error_handler,
    )


disclosure_verifier_agent = FanOutAgent(
    name="DisclosureVerifier",
    config=FanOutConfig(
        prepare_work_items=_prepare_work_items,
        create_agent=_create_verifier_agent,
        output_key="disclosure_all_findings",
        results_field="findings",
        batch_size=4,
        empty_message="No applicable standards found to verify.",
    ),
)
