"""FanOutDisclosureVerifier - Custom agent for parallel disclosure verification."""
import re
from typing import AsyncGenerator
from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types
from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from .schema import VerifierAgentOutput
from .prompt import get_verifier_instruction
from ...tools.checklist_loader import load_standard_checklist


class FanOutDisclosureVerifier(BaseAgent):
    """
    Custom agent that dynamically spawns parallel disclosure verifiers,
    one per applicable standard identified by ScannerAgent.

    Maintains ADK observability by using ParallelAgent internally.
    """

    name: str = "FanOutDisclosureVerifier"
    description: str = "Spawns parallel verifiers for each applicable IFRS/IAS standard"

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Read applicable standards from session state (set by ScannerAgent)
        scanner_output = ctx.session.state.get("scanner_output", {})
        applicable_standards = scanner_output.get("applicable_standards", [])

        if not applicable_standards:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[types.Part(text="No applicable standards found to verify.")]
                )
            )
            return

        # 2. Create fresh VerifierAgent instances (single-parent rule)
        verifier_agents = []
        for standard_code in applicable_standards:
            try:
                # Load checklist for this standard
                checklist = load_standard_checklist(standard_code)

                # Create verifier agent for this standard
                sanitized_code = re.sub(r'[^a-zA-Z0-9_]', '_', standard_code)
                agent = create_disclosure_verifier_agent(
                    name=f"verify_{sanitized_code}",
                    standard_code=standard_code,
                    checklist=checklist,
                    output_key=f"disclosure_findings:{standard_code}"
                )
                verifier_agents.append(agent)

            except ValueError as e:
                # Standard not in checklist - skip it
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="agent",
                        parts=[types.Part(text=f"Skipping {standard_code}: {str(e)}")]
                    )
                )
                continue

        if not verifier_agents:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[types.Part(text="No verifiable standards found in checklist.")]
                )
            )
            return

        # 3. Batch processing to avoid rate limits (429 RESOURCE_EXHAUSTED)
        BATCH_SIZE = 4
        for i in range(0, len(verifier_agents), BATCH_SIZE):
            batch = verifier_agents[i : i + BATCH_SIZE]
            
            # Wrap in ParallelAgent for concurrent execution of this batch
            parallel = ParallelAgent(
                name=f"disclosure_verifier_parallel_batch_{i // BATCH_SIZE + 1}",
                sub_agents=batch
            )

            # 4. Yield all events (preserves ADK observability)
            async for event in parallel.run_async(ctx):
                yield event


def create_disclosure_verifier_agent(
    name: str,
    standard_code: str,
    checklist: dict,
    output_key: str
) -> LlmAgent:
    """
    Factory to create a fresh disclosure verifier for a specific standard.
    Must create new instances each time (ADK single-parent rule).

    Args:
        name: Agent name
        standard_code: IFRS/IAS standard code (e.g., "IAS 1")
        checklist: Loaded checklist data for the standard
        output_key: Session state key for output
    """
    # Build enhanced instruction with checklist data
    base_instruction = get_verifier_instruction(standard_code)

    # Add checklist disclosure requirements to instruction
    disclosures_text = f"\n\n## Disclosure Checklist for {standard_code}\n\n"
    disclosures_text += f"Standard: {checklist['name']}\n\n"
    disclosures_text += "Required disclosures to check:\n\n"

    for disclosure in checklist['disclosures']:
        disclosures_text += f"- **{disclosure['id']}**: {disclosure['requirement']}\n"
        if disclosure['description'] != disclosure['requirement']:
            disclosures_text += f"  Details: {disclosure['description']}\n"
        disclosures_text += "\n"

    full_instruction = base_instruction + disclosures_text

    return LlmAgent(
        name=name,
        model="gemini-3-pro-preview",
        instruction=full_instruction,
        output_key=output_key,
        output_schema=VerifierAgentOutput,
        generate_content_config=types.GenerateContentConfig(
            http_options=types.HttpOptions(retry_options=get_default_retry_config())
        ),
        on_model_error_callback=default_model_error_handler,
    )


# Singleton instance for import
disclosure_verifier_agent = FanOutDisclosureVerifier()
