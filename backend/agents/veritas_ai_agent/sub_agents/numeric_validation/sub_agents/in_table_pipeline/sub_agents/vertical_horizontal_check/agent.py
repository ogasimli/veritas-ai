"""Agent factory for batched vertical and horizontal check agents.

Architecture
------------
Instead of a single LlmAgent per check type, checks are orchestrated by a
`BatchedCheckAgent`. This agent:
1.  **Splits input tables** into chunks (max 15 tables) to fit within context windows.
2.  **Fans out** parallel ephemeral sub-agents for each batch.
3.  **Aggregates** results from all batches into a unified output.

Factory Functions
-----------------
*   `create_vertical_check_agent()`: Returns a `BatchedCheckAgent` configured with `VERTICAL_INSTRUCTION`.
*   `create_horizontal_check_agent()`: Returns a `BatchedCheckAgent` configured with `HORIZONTAL_INSTRUCTION`.

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
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from .prompt import HORIZONTAL_INSTRUCTION, VERTICAL_INSTRUCTION
from .schema import HorizontalVerticalCheckAgentOutput
from .utils import chunk_tables


class BatchedCheckAgent(BaseAgent):
    """Orchestrates parallel execution of horizontal and vertical check agents on batches of tables.

    Splits input tables into evenly distributed batches to avoid attention window limits.
    """

    instruction_template: str = ""
    output_key: str = ""

    def __init__(self, name: str, instruction: str, output_key: str):
        super().__init__(name=name)
        self.instruction_template = instruction
        self.output_key = output_key

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Retrieve and parse tables
        extracted_tables_json = ctx.session.state.get("extracted_tables", "[]")
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
            # Nothing to do
            ctx.session.state[self.output_key] = {"formulas": []}
            return

        # 2. Chunk tables
        batches = chunk_tables(tables, max_size=15)

        # 3. Create sub-agents for each batch
        sub_agents = []
        for i, batch_tables in enumerate(batches):
            # Serialize the batch for prompt injection
            batch_json = json.dumps({"tables": batch_tables}, indent=2)

            # Format the instruction with the specific batch
            # Note: Using .replace() instead of .format() because the instruction
            # template contains curly braces for JSON examples which conflict with .format().
            batch_instruction = self.instruction_template.replace(
                "{extracted_tables}", batch_json
            )

            agent = LlmAgent(
                name=f"{self.name}_{i}",
                model="gemini-3-pro-preview",
                instruction=batch_instruction,
                output_schema=HorizontalVerticalCheckAgentOutput,
                # Use a temp key for per-batch output to avoid overwriting
                output_key=f"{self.output_key}_batch_{i}",
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
            sub_agents.append(agent)

        # 4. Run in parallel
        if sub_agents:
            runner = ParallelAgent(
                name=f"{self.name}_ParallelRunner", sub_agents=sub_agents
            )
            async for event in runner.run_async(ctx):
                yield event

        # 5. Aggregate results
        all_formulas = []
        for i in range(len(batches)):
            batch_key = f"{self.output_key}_batch_{i}"
            batch_output = ctx.session.state.get(batch_key)
            if not batch_output:
                continue

            if hasattr(batch_output, "model_dump"):
                batch_output = batch_output.model_dump()

            formulas = batch_output.get("formulas", [])
            all_formulas.extend(formulas)

            # Cleanup temp key
            # ctx.session.state.pop(batch_key, None) # Optional: cleanup

        # 6. Write final aggregated output
        ctx.session.state[self.output_key] = {"formulas": all_formulas}


def create_vertical_check_agent() -> BaseAgent:
    """Create the vertical check agent (batched)."""
    return BatchedCheckAgent(
        name="VerticalCheckAgent",
        instruction=VERTICAL_INSTRUCTION,
        output_key="vertical_check_output",
    )


def create_horizontal_check_agent() -> BaseAgent:
    """Create the horizontal check agent (batched)."""
    return BatchedCheckAgent(
        name="HorizontalCheckAgent",
        instruction=HORIZONTAL_INSTRUCTION,
        output_key="horizontal_check_output",
    )
