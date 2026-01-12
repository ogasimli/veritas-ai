"""FanOutVerifierAgent - CustomAgent for dynamic parallel verification."""
from typing import AsyncGenerator
from google.adk.agents import BaseAgent, ParallelAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types

from .verifier import create_verifier_agent


class FanOutVerifierAgent(BaseAgent):
    """
    CustomAgent that dynamically spawns parallel VerifierAgents,
    one per FSLI extracted by ExtractorAgent.

    Maintains ADK observability by using ParallelAgent internally.
    """

    name: str = "FanOutVerifierAgent"
    description: str = "Spawns parallel verifiers for each FSLI"

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Read FSLI names from session state (set by ExtractorAgent)
        extractor_output = ctx.session.get("extractor_output", {}) # Plan says session.state but ADK ctx usually has ctx.session
        fsli_names = extractor_output.get("fsli_names", [])

        if not fsli_names:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[types.Part(text="No FSLIs found to verify.")]
                )
            )
            return

        # 2. Create fresh VerifierAgent instances (single-parent rule)
        verifier_agents = [
            create_verifier_agent(
                name=f"verify_{fsli_name.replace(' ', '_').replace('/', '_')}",
                fsli_name=fsli_name,
                output_key=f"checks:{fsli_name}"
            )
            for fsli_name in fsli_names
        ]

        # 3. Wrap in ParallelAgent for concurrent execution
        parallel = ParallelAgent(
            name="verifier_parallel_block",
            sub_agents=verifier_agents
        )

        # 4. Yield all events (preserves ADK observability)
        async for event in parallel.run_async(ctx):
            yield event


# Singleton instance for import
fan_out_verifier_agent = FanOutVerifierAgent()
