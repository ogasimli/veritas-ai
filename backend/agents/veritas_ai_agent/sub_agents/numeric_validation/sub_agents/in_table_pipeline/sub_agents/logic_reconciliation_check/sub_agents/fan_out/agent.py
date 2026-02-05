"""Logic Reconciliation Check Fan-Out Agent."""

import json
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from .....schema import CheckAgentOutput
from .prompt import get_table_instruction


class LogicReconciliationFormulaInferer(BaseAgent):
    """Dynamic fan-out for logic reconciliation checks."""

    def __init__(self):
        super().__init__(name="LogicReconciliationFormulaInferer")

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Run fan-out logic."""
        # 1. Get candidate indexes from screener output
        screener_output = ctx.session.state.get(
            "logic_reconciliation_check_screener_output", {}
        )
        if hasattr(screener_output, "model_dump"):
            screener_output = screener_output.model_dump()

        candidates = screener_output.get("candidate_table_indexes", [])

        # 2. Filter extracted tables
        all_tables_json = ctx.session.state.get("extracted_tables", "[]")
        if isinstance(all_tables_json, str):
            try:
                all_tables = json.loads(all_tables_json)
            except json.JSONDecodeError:
                all_tables = []
        else:
            all_tables = all_tables_json

        candidate_tables = []
        # Support if all_tables is a dict with "tables" key or just a list
        tables_list = (
            all_tables if isinstance(all_tables, list) else all_tables.get("tables", [])
        )

        for idx in candidates:
            matching_table = next(
                (t for t in tables_list if t.get("table_index") == idx), None
            )
            if matching_table:
                candidate_tables.append(matching_table)

        # 3. Early return if no candidates
        if not candidate_tables:
            ctx.session.state["logic_reconciliation_formula_inferer_output"] = {
                "formulas": []
            }
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[
                        types.Part(text="No candidate tables for logic reconciliation.")
                    ],
                ),
            )
            return

        # 4. Create per-table agents
        agents = []
        for table in candidate_tables:
            t_idx = table.get("table_index")
            # Envelope: {"tables": [table]}
            table_envelope = json.dumps({"tables": [table]})
            agents.append(_create_table_agent(t_idx, table_envelope))

        # 5. Run agents in parallel
        parallel_agent = ParallelAgent(
            name="LogicReconciliationCheckParallel", sub_agents=agents
        )

        async for event in parallel_agent.run_async(ctx):
            yield event

        # 6. Aggregate per-table outputs
        aggregated_formulas = []
        for table in candidate_tables:
            t_idx = table.get("table_index")
            key = f"logic_reconciliation_formula_inferer_table_output_{t_idx}"
            output = ctx.session.state.get(key, {})
            if hasattr(output, "model_dump"):
                output = output.model_dump()

            # formulas is list[str] (actually list[InferredFormula] in schema, but dict in state)
            formulas = output.get("formulas", [])
            aggregated_formulas.extend(formulas)

        ctx.session.state["logic_reconciliation_formula_inferer_output"] = {
            "formulas": aggregated_formulas
        }


def _create_table_agent(table_index: int, table_json: str) -> LlmAgent:
    """Create a check agent for a specific table."""
    return LlmAgent(
        name=f"LogicReconciliationFormulaInfererTableAgent_{table_index}",
        model="gemini-3-pro-preview",
        instruction=get_table_instruction(table_json),
        output_schema=CheckAgentOutput,
        output_key=f"logic_reconciliation_formula_inferer_table_output_{table_index}",
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
