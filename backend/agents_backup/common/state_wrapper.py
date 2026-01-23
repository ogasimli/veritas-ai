from typing import AsyncGenerator
from google.adk.agents import BaseAgent, InvocationContext
from google.adk.events import Event
from google.genai import types

from pydantic import PrivateAttr

class StateAwareWrapperAgent(BaseAgent):
    """
    Wrapper agent that tracks execution state in the session context.
    Increments a counter in session state when starting, and decrements when finishing.
    Useful for other agents to know how many "heavy" agents are currently running.
    """
    _inner_agent: BaseAgent = PrivateAttr()
    _counter_key: str = PrivateAttr()

    def __init__(self, inner_agent: BaseAgent, counter_key: str = "active_heavy_agents"):
        super().__init__(
            name=inner_agent.name,
            description=inner_agent.description
        )
        self._inner_agent = inner_agent
        self._counter_key = counter_key

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Increment counter
        current_count = ctx.session.state.get(self._counter_key, 0)
        ctx.session.state[self._counter_key] = current_count + 1
        
        try:
            # Delegate to inner agent
            async for event in self._inner_agent.run_async(ctx):
                yield event
        finally:
            # Decrement counter
            current_count = ctx.session.state.get(self._counter_key, 1)
            ctx.session.state[self._counter_key] = max(0, current_count - 1)
