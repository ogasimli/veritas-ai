"""Fan-Out Agent pattern - parallel work distribution with batching.

Exports
-------
FanOutAgent : BaseAgent
    Main agent that orchestrates fan-out parallel execution
FanOutConfig : dataclass
    Configuration including work-item preparation, agent factory, and aggregation
"""

from .agent import FanOutAgent
from .config import FanOutConfig

__all__ = [
    "FanOutAgent",
    "FanOutConfig",
]
