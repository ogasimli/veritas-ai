"""FanOutAgent: generic parallel work distribution pattern.

Reads input from state, splits into work items, creates an LlmAgent per item,
runs them in parallel (optionally batched for rate limits), and aggregates
results back into state.

This agent follows Google ADK's recommended pattern for dynamic parallel workflows:
ParallelAgent instances are created at runtime inside _run_async_impl based on
runtime data, rather than being registered statically in __init__.
"""

import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from .config import FanOutConfig

logger = logging.getLogger(__name__)


class FanOutAgent(BaseAgent):
    """Reusable agent that fans out work items to parallel LlmAgents.

    Parameters
    ----------
    name : str
        Agent name (used as prefix for child agent output keys).
    config : FanOutConfig
        Complete configuration including work-item preparation, agent factory,
        and aggregation logic.
    description : str | None, optional
        Agent description for tool use/delegation provided as metadata, by default None.
    """

    config: FanOutConfig | None = None

    def __init__(
        self,
        name: str,
        config: FanOutConfig,
        description: str | None = None,
    ):
        if description:
            super().__init__(name=name, description=description)
        else:
            super().__init__(name=name)
        self.config = config

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        assert self.config is not None
        state = ctx.session.state

        # 1. Prepare work items
        items = self.config.prepare_work_items(state)

        # 2. Early exit
        if not items:
            state[self.config.output_key] = {self.config.results_field: []}
            if self.config.empty_message:
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="agent",
                        parts=[types.Part(text=self.config.empty_message)],
                    ),
                )
            return

        # 3. Create agents with deterministic output keys
        agents = []
        output_keys = []
        for i, item in enumerate(items):
            key = f"{self.name}_item_{i}"
            agent = self.config.create_agent(i, item, key)
            agents.append(agent)
            output_keys.append(key)

        # 4. Build ParallelAgent wrappers (batched if needed)
        batch_size = self.config.batch_size or len(agents)
        parallel_agents = []
        for start in range(0, len(agents), batch_size):
            batch = agents[start : start + batch_size]
            parallel = ParallelAgent(
                name=f"{self.name}_batch_{start // batch_size}",
                sub_agents=batch,
            )
            parallel_agents.append(parallel)

        # 5. Execute (sequential across batches, parallel within each batch)
        # Note: ParallelAgent instances are not registered to self.sub_agents as per
        # ADK best practices for dynamic agent creation (see Google ADK documentation)
        for parallel in parallel_agents:
            async for event in parallel.run_async(ctx):
                yield event

        # 6. Collect & normalize outputs
        outputs = []
        for key in output_keys:
            output = state.get(key)
            if output is None:
                continue
            if hasattr(output, "model_dump"):
                output = output.model_dump()
            outputs.append(output)

        # 7. Aggregate
        if self.config.aggregate:
            result = self.config.aggregate(outputs)
        else:
            all_items = []
            for output in outputs:
                all_items.extend(output.get(self.config.results_field, []))
            result = {self.config.results_field: all_items}

        state[self.config.output_key] = result

        logger.info(
            "%s: processed %d work items, produced %d %s",
            self.name,
            len(items),
            len(result.get(self.config.results_field, []))
            if isinstance(result, dict)
            else "N/A",
            self.config.results_field,
        )
