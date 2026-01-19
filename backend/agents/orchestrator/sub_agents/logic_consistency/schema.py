from typing import List
from pydantic import BaseModel

# Import from reviewer (final output)
from .sub_agents.reviewer.schema import RefinedFinding

class LogicConsistencyOutput(BaseModel):
    """Output from logic consistency agent (after Detector→Reviewer pipeline)."""
    findings: List[RefinedFinding]
