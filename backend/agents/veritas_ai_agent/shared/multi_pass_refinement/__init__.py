"""Multi-Pass Refinement Agent pattern - N parallel chains x M sequential passes.

Exports
-------
MultiPassRefinementAgent : BaseAgent
    Main agent that orchestrates NxM refinement pattern
MultiPassRefinementConfig : dataclass
    Runtime configuration for refinement parameters
LlmAgentConfig : dataclass
    Configuration for individual agents using ADK's native config objects
MultiPassRefinementProtocol : Protocol
    Interface for concrete implementations
"""

from .agent import MultiPassRefinementAgent
from .config import LlmAgentConfig, MultiPassRefinementConfig
from .protocols import MultiPassRefinementProtocol

__all__ = [
    "LlmAgentConfig",
    "MultiPassRefinementAgent",
    "MultiPassRefinementConfig",
    "MultiPassRefinementProtocol",
]
