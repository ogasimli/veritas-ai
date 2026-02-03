"""InTableFormulaFanOut - CustomAgent that batches tables by complexity
and fans out one LlmAgent per batch via ParallelAgent.

Design notes
------------
* Batching logic lives in module-level helpers so it can be unit-tested
  without instantiating the agent.
* Sub-agents are created fresh each invocation (ADK single-parent rule).
* Each sub-agent writes its structured output to a unique state key
  ``in_table_batch_output_<i>``.  After every batch completes the
  aggregation loop reads those keys, stamps ``check_type="in_table"``, and
  appends entries to the shared ``state["reconstructed_formulas"]`` list.
* Batches are processed sequentially (one ParallelAgent per batch) to
  stay within rate limits - mirrors the pattern used by
  ``LegacyNumericVerifier``.
"""

import json
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from .prompt import get_batch_instruction
from .schema import InTableBatchOutput
from .table_batching import batch_tables_by_complexity

# ---------------------------------------------------------------------------
# Sub-agent factory
# ---------------------------------------------------------------------------


def _create_batch_agent(batch_index: int, tables_json: str) -> LlmAgent:
    """Return a fresh LlmAgent for one batch.

    The instruction is built dynamically so that the table data is
    embedded directly - no shared-state key collision between parallel
    sub-agents.
    """
    return LlmAgent(
        name=f"in_table_batch_{batch_index}",
        model="gemini-3-pro-preview",
        instruction=get_batch_instruction(tables_json),
        output_key=f"in_table_batch_output_{batch_index}",
        output_schema=InTableBatchOutput,
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


# ---------------------------------------------------------------------------
# Fan-out agent
# ---------------------------------------------------------------------------


class InTableFormulaFanOut(BaseAgent):
    """CustomAgent: batch tables, fan out LlmAgents, aggregate results."""

    name: str = "InTableFormulaFanOut"
    description: str = (
        "Fans out parallel LLM agents to propose in-table formulas, "
        "one batch per complexity group."
    )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Read extracted tables from state
        tables = ctx.session.state.get("extracted_tables", {}).get("tables", [])

        if not tables:
            ctx.session.state.setdefault("reconstructed_formulas", [])
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[types.Part(text="No extracted tables found; skipping.")],
                ),
            )
            return

        # 2. Compute batches
        batches = batch_tables_by_complexity(tables)

        # 3. Sequential batch loop (rate-limit friendly)
        for batch_idx, batch in enumerate(batches):
            # Wrap in a dict to match the prompt's expected "Input Format"
            tables_json = json.dumps({"tables": batch})
            agent = _create_batch_agent(batch_idx, tables_json)

            parallel = ParallelAgent(
                name=f"in_table_parallel_{batch_idx}",
                sub_agents=[agent],
            )

            async for event in parallel.run_async(ctx):
                yield event

        # 4. Aggregate all batch outputs into the shared state list
        ctx.session.state.setdefault("reconstructed_formulas", [])

        for key in list(ctx.session.state.keys()):
            if not key.startswith("in_table_batch_output_"):
                continue
            output = ctx.session.state[key]
            if hasattr(output, "model_dump"):
                output = output.model_dump()

            # output["formulas"] is now list[str]
            for formula_str in output.get("formulas", []):
                ctx.session.state["reconstructed_formulas"].append(
                    {
                        "check_type": "in_table",
                        "target_cells": [],  # Identified by engine later
                        "actual_value": None,
                        "inferred_formulas": [{"formula": formula_str}],
                    }
                )


# ---------------------------------------------------------------------------
# Module-level singleton for import
# ---------------------------------------------------------------------------

in_table_pipeline_agent = InTableFormulaFanOut()
