"""FanOutAgent: generic parallel work distribution pattern.

Reads input from state, splits into work items, creates an LlmAgent per item,
runs them concurrently (throttled by a global semaphore), and aggregates
results back into state.

Concurrency is controlled by a process-wide ``asyncio.Semaphore`` whose limit
is set via the ``FANOUT_MAX_CONCURRENCY`` environment variable (default: 10).
This prevents exceeding Gemini API rate limits regardless of how many
FanOutAgent instances are active.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from .config import FanOutConfig

logger = logging.getLogger(__name__)

_MAX_CONCURRENCY = int(os.environ.get("FANOUT_MAX_CONCURRENCY", "8"))
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Lazily create the semaphore on first use (must happen inside an event loop)."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
    return _semaphore


class FanOutAgent(BaseAgent):
    """Reusable agent that fans out work items to concurrent LlmAgents.

    Concurrency across all FanOutAgent instances in the process is capped by
    a shared ``asyncio.Semaphore`` (configured via ``FANOUT_MAX_CONCURRENCY``).

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
        **kwargs,
    ):
        super_kwargs = {"name": name, **kwargs}
        if description:
            super_kwargs["description"] = description
        super().__init__(**super_kwargs)
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
            empty_result = {self.config.results_field: []}
            state[self.config.output_key] = empty_result
            yield Event(
                author=self.name,
                content=types.Content(
                    role="agent",
                    parts=[
                        types.Part(text=self.config.empty_message or "No work items.")
                    ],
                ),
                actions=EventActions(
                    state_delta={self.config.output_key: empty_result},
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

        # 4. Run all agents concurrently, throttled by global semaphore
        semaphore = _get_semaphore()

        async def _run_agent(agent: BaseAgent) -> list[Event]:
            async with semaphore:
                events = []
                async for event in agent.run_async(ctx):
                    events.append(event)
                return events

        tasks = [asyncio.create_task(_run_agent(agent)) for agent in agents]
        for completed in asyncio.as_completed(tasks):
            for event in await completed:
                yield event

        # 5. Collect & normalize outputs
        outputs = []
        for key in output_keys:
            output = state.get(key)
            if output is None:
                continue
            if hasattr(output, "model_dump"):
                output = output.model_dump()
            outputs.append(output)

        # 6. Aggregate
        if self.config.aggregate:
            result = self.config.aggregate(outputs)
        else:
            all_items = []
            for output in outputs:
                all_items.extend(output.get(self.config.results_field, []))
            result = {self.config.results_field: all_items}

        state[self.config.output_key] = result

        # Yield an event carrying the state delta so the output is visible
        # in the event stream (for processors, debug YAML, fixtures, etc.).
        result_count = (
            len(result.get(self.config.results_field, []))
            if isinstance(result, dict)
            else "N/A"
        )
        yield Event(
            author=self.name,
            content=types.Content(
                role="agent",
                parts=[
                    types.Part(
                        text=f"Aggregated {result_count} {self.config.results_field}."
                    )
                ],
            ),
            actions=EventActions(
                state_delta={self.config.output_key: result},
            ),
        )

        logger.info(
            "%s: processed %d work items, produced %s %s (max_concurrency=%d)",
            self.name,
            len(items),
            result_count,
            self.config.results_field,
            _MAX_CONCURRENCY,
        )
