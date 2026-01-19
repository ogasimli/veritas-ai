from typing import List
from pydantic import BaseModel

class LogicFinding(BaseModel):
    """A logic consistency finding."""
    fsli_name: str                   # Financial statement line item
    claim: str                       # The claim being made
    contradiction: str               # Why it's logically inconsistent
    severity: str                    # "high" | "medium" | "low"
    reasoning: str                   # Detailed reasoning chain
    source_refs: List[str]           # Source references in document

class DetectorAgentOutput(BaseModel):
    """Output from logic detector agent."""
    findings: List[LogicFinding]
