"""Disclosure compliance agent package."""
from .agent import disclosure_compliance_agent

# Alias for ADK Cloud Run deployment
root_agent = disclosure_compliance_agent

__all__ = ['disclosure_compliance_agent', 'root_agent']
