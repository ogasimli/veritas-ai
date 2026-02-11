"""Plugin to skip agents not selected by the user."""

from typing import ClassVar

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types


class AgentSelectionPlugin(BasePlugin):
    """Skips agents whose name is not in the ``enabled_agents`` state list.

    The processor injects ADK agent names (PascalCase) into
    ``state["enabled_agents"]``.  If the key is absent, all agents run
    (backwards-compatible default).

    Only the four top-level selectable agents are subject to filtering;
    sub-agents (e.g. "TableNamer") always pass through.
    """

    _SELECTABLE: ClassVar[frozenset[str]] = frozenset(
        {
            "NumericValidation",
            "LogicConsistency",
            "DisclosureCompliance",
            "ExternalSignal",
        }
    )

    def __init__(self):
        super().__init__(name="agent_selection")

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        enabled = callback_context.state.get("enabled_agents")
        if enabled is None:
            return None  # No filter — run everything

        if agent.name in self._SELECTABLE and agent.name not in enabled:
            return types.Content(
                role="model",
                parts=[types.Part(text=f"Agent {agent.name} skipped (not selected).")],
            )

        return None
