"""CrossTableFormulaFanOut - CustomAgent that chunks FSLIs and fans out
LlmAgents in parallel per chunk.

Design notes
------------
* FSLI list = ``primary_fsli`` + ``sub_fsli`` from
  ``state["fsli_extractor_output"]``.
* Chunk size is controlled by the ``FSLI_BATCH_SIZE`` env var (default 5).
* Sub-agents are created fresh each invocation (ADK single-parent rule).
* Each sub-agent writes to ``cross_table_batch_output_<i>``.  After all
  chunks complete the aggregation loop stamps ``check_type="cross_table"``
  and appends to the shared ``state["reconstructed_formulas"]`` list.
* Chunks are processed sequentially (one ParallelAgent per chunk) to
  stay within rate limits.
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

from .chunking import FSLI_BATCH_SIZE, chunk_fsli_list
from .prompt import get_batch_instruction
from .schema import CrossTableBatchOutput

# ---------------------------------------------------------------------------
# Sub-agent factory
# ---------------------------------------------------------------------------


def _create_chunk_agent(
    chunk_index: int, fsli_batch_json: str, tables_json: str
) -> LlmAgent:
    """Return a fresh LlmAgent for one FSLI chunk."""
    return LlmAgent(
        name=f"cross_table_batch_{chunk_index}",
        model="gemini-3-pro-preview",
        instruction=get_batch_instruction(fsli_batch_json, tables_json),
        output_key=f"cross_table_batch_output_{chunk_index}",
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


# ---------------------------------------------------------------------------
# Fan-out agent
# ---------------------------------------------------------------------------


class CrossTableFormulaFanOut(BaseAgent):
    """CustomAgent: chunk FSLIs, fan out LlmAgents, aggregate results."""

    name: str = "CrossTableFormulaFanOut"
    description: str = (
        "Fans out parallel LLM agents to propose cross-table formulas, "
        "one batch per FSLI chunk."
    )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Read FSLI lists from state (written by FsliExtractor)
        extractor_output = ctx.session.state.get("fsli_extractor_output", {})
        if hasattr(extractor_output, "model_dump"):
            extractor_output = extractor_output.model_dump()

        primary = extractor_output.get("primary_fsli", [])
        sub = extractor_output.get("sub_fsli", [])
        all_fslis = primary + sub

        if not all_fslis:
            ctx.session.state.setdefault("reconstructed_formulas", [])
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[types.Part(text="No FSLIs to analyse; skipping.")],
                ),
            )
            return

        # 2. Read extracted tables (needed by each sub-agent prompt)
        extracted_tables = ctx.session.state.get("extracted_tables", {})
        tables_json = json.dumps(extracted_tables)

        # 3. Chunk FSLIs
        chunks = chunk_fsli_list(all_fslis, FSLI_BATCH_SIZE)

        # 4. Sequential chunk loop
        for chunk_idx, chunk in enumerate(chunks):
            fsli_batch_json = json.dumps(chunk)
            agent = _create_chunk_agent(chunk_idx, fsli_batch_json, tables_json)

            parallel = ParallelAgent(
                name=f"cross_table_parallel_{chunk_idx}",
                sub_agents=[agent],
            )

            async for event in parallel.run_async(ctx):
                yield event

        # 5. Aggregate all chunk outputs into the shared state list
        ctx.session.state.setdefault("reconstructed_formulas", [])

        for key in list(ctx.session.state.keys()):
            if not key.startswith("cross_table_batch_output_"):
                continue
            output = ctx.session.state[key]
            if hasattr(output, "model_dump"):
                output = output.model_dump()

            # output["formulas"] is now list[str]
            for formula_str in output.get("formulas", []):
                ctx.session.state["reconstructed_formulas"].append(
                    {
                        "check_type": "cross_table",
                        "inferred_formulas": [{"formula": formula_str}],
                    }
                )


# ---------------------------------------------------------------------------
# Module-level singleton for import
# ---------------------------------------------------------------------------

cross_table_fan_out_agent = CrossTableFormulaFanOut()
