"""Numeric validation agent package."""

from .agent import numeric_validation_agent

# Alias for ADK Cloud Run deployment
root_agent = numeric_validation_agent

__all__ = ["numeric_validation_agent", "root_agent"]
