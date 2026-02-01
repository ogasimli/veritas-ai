"""FanOutVerifierAgent - CustomAgent for dynamic parallel verification."""

import re
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.events import Event
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from .prompt import get_verifier_instruction
from .schema import LegacyNumericVerifierOutput


class LegacyNumericVerifier(BaseAgent):
    """
    CustomAgent that dynamically spawns parallel VerifierAgents,
    one per FSLI extracted by LegacyNumericFsliExtractor.

    Maintains ADK observability by using ParallelAgent internally.
    """

    name: str = "LegacyNumericVerifier"
    description: str = "Spawns parallel verifiers for each FSLI"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Read FSLI names from session state (set by LegacyNumericFsliExtractor)
        extractor_output = ctx.session.state.get(
            "legacy_numeric_fsli_extractor_output", {}
        )
        fsli_names = extractor_output.get("fsli_names", [])

        if not fsli_names:
            ctx.session.state["legacy_numeric_all_checks"] = []
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent", parts=[types.Part(text="No FSLIs found to verify.")]
                ),
            )
            return

        # 2. Create fresh VerifierAgent instances (single-parent rule)
        verifier_agents = [
            create_verifier_agent(
                name=f"verify_{re.sub(r'[^a-zA-Z0-9_]', '_', fsli_name)}",
                fsli_name=fsli_name,
                output_key=f"legacy_numeric_checks:{fsli_name}",
            )
            for fsli_name in fsli_names
        ]

        # 3. Adaptive batch processing to avoid rate limits (429 RESOURCE_EXHAUSTED)
        batch_id = 1
        current_index = 0
        total_agents = len(verifier_agents)

        while current_index < total_agents:
            # Check if other heavy agents are running
            active_heavy_agents = ctx.session.state.get("active_heavy_agents", 0)

            # Dynamic batch sizing
            if active_heavy_agents > 0:
                # Aggressive throttling when others are running
                current_batch_size = 1
            else:
                # Speed up when running alone
                current_batch_size = 10

            batch = verifier_agents[current_index : current_index + current_batch_size]

            parallel = ParallelAgent(
                name=f"verifier_parallel_batch_{batch_id}", sub_agents=batch
            )

            # 4. Yield all events (preserves ADK observability)
            async for event in parallel.run_async(ctx):
                yield event

            current_index += current_batch_size
            batch_id += 1

        # 5. After all verifiers complete, aggregate results
        all_checks = []
        for key in ctx.session.state:
            if key.startswith("legacy_numeric_checks:"):
                checks_data = ctx.session.state[key]
                if checks_data and "checks" in checks_data:
                    all_checks.extend(checks_data["checks"])
        ctx.session.state["legacy_numeric_all_checks"] = all_checks


def create_verifier_agent(name: str, fsli_name: str, output_key: str) -> LlmAgent:
    """
    Factory to create a fresh VerifierAgent for a specific FSLI.
    Must create new instances each time (ADK single-parent rule).
    """
    return LlmAgent(
        name=name,
        model="gemini-3-pro-preview",
        instruction=get_verifier_instruction(fsli_name),
        output_key=output_key,
        output_schema=LegacyNumericVerifierOutput,
        code_executor=BuiltInCodeExecutor(),
        generate_content_config=types.GenerateContentConfig(
            http_options=types.HttpOptions(retry_options=get_default_retry_config())
        ),
        on_model_error_callback=default_model_error_handler,
    )


# Singleton instance for import
verifier_agent = LegacyNumericVerifier()
