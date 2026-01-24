"""Logic consistency agent package."""
from .agent import logic_consistency_agent

# Alias for ADK Cloud Run deployment
root_agent = logic_consistency_agent

__all__ = ['logic_consistency_agent', 'root_agent']
