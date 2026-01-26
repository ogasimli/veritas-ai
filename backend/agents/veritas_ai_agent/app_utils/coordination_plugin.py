"""Agent Coordination Plugin for tracking heavy agent activity."""

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types


class AgentCoordinationPlugin(BasePlugin):
    """
    Plugin to track active heavy agents globally.

    Increments a counter in session state when specified "heavy" agents start,
    and decrements when they finish. Other agents (like FanOutVerifierAgent)
    can read this counter to adjust their batch sizes dynamically.
    """

    def __init__(
        self,
        heavy_agent_names: set[str],
        counter_key: str = "active_heavy_agents",
    ):
        """
        Initialize the plugin.

        Args:
            heavy_agent_names: Names of agents considered "heavy" (resource-intensive).
            counter_key: Session state key for the counter.
        """
        super().__init__(name="agent_coordination")
        self.heavy_agent_names = heavy_agent_names
        self.counter_key = counter_key

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        """Increment counter when a heavy agent starts."""
        if agent.name in self.heavy_agent_names:
            count = callback_context.state.get(self.counter_key, 0)
            callback_context.state[self.counter_key] = count + 1
        return None  # Don't short-circuit execution

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        """Decrement counter when a heavy agent finishes."""
        if agent.name in self.heavy_agent_names:
            count = callback_context.state.get(self.counter_key, 1)
            callback_context.state[self.counter_key] = max(0, count - 1)
        return None


# Default configuration for Veritas AI
DEFAULT_HEAVY_AGENTS = {
    "logic_consistency",
    "disclosure_compliance",
    "external_signal",
}


def create_coordination_plugin() -> AgentCoordinationPlugin:
    """Factory function to create the default coordination plugin."""
    return AgentCoordinationPlugin(heavy_agent_names=DEFAULT_HEAVY_AGENTS)
