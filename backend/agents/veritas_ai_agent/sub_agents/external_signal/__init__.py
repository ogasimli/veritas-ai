"""External Signal agent with bidirectional Deep Research verification."""

from .agent import external_signal_agent

# Alias for ADK Cloud Run deployment
root_agent = external_signal_agent

__all__ = ["external_signal_agent", "root_agent"]
