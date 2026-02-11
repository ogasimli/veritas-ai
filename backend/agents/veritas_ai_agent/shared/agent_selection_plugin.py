"""Plugin to skip agents not selected by the user."""

import os
from typing import ClassVar

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types


class AgentSelectionPlugin(BasePlugin):
    """Skips agents whose name is not in the ``enabled_agents`` list.

    **Audit agent** filtering is resolved in priority order:

    1. **Session state** - ``state["enabled_agents"]`` (injected by the
       processor at runtime).
    2. **Environment variable** - ``VERITAS_AGENT_MODE``.  When set to a
       real ADK agent name (e.g. ``NumericValidation``), only that agent
       is enabled.  The special value ``orchestrator`` (the default)
       enables all agents.
    3. **No filter** - if neither source is present, all agents run
       (backwards-compatible default).

    **DocumentValidator** is controlled independently via the
    ``VERITAS_DOCUMENT_VALIDATOR_ENABLED`` env var (default ``true``).

    Sub-agents (e.g. "TableNamer") always pass through.
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

        # --- Audit agent filtering (VERITAS_AGENT_MODE) ---
        # Resolved once at startup so standalone deployments (via
        # ``make deploy-agent``) filter through this plugin instead of
        # swapping the root agent.
        mode = os.environ.get("VERITAS_AGENT_MODE", "orchestrator")
        if mode == "orchestrator":
            self._env_enabled: list[str] | None = None  # run all
        elif mode in self._SELECTABLE:
            self._env_enabled = [mode]
        else:
            self._env_enabled = None  # unknown mode - run all

        # --- DocumentValidator toggle (VERITAS_DOCUMENT_VALIDATOR_ENABLED) ---
        self._document_validator_enabled = os.environ.get(
            "VERITAS_DOCUMENT_VALIDATOR_ENABLED", "true"
        ).lower() in ("true", "1", "yes")

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        # DocumentValidator controlled independently by its own env var.
        if agent.name == "DocumentValidator":
            if not self._document_validator_enabled:
                return types.Content(
                    role="model",
                    parts=[types.Part(text="DocumentValidator skipped (disabled).")],
                )
            return None

        # Session state (processor-injected) takes priority over env var.
        enabled = callback_context.state.get("enabled_agents")
        if enabled is None:
            enabled = self._env_enabled

        if enabled is None:
            return None  # No filter - run everything

        if agent.name in self._SELECTABLE and agent.name not in enabled:
            return types.Content(
                role="model",
                parts=[types.Part(text=f"Agent {agent.name} skipped (not selected).")],
            )

        return None
