from typing import List
from pydantic import BaseModel

class RefinedFinding(BaseModel):
    fsli_name: str
    claim: str
    contradiction: str
    severity: str  # "high" | "medium" | "low"
    reasoning: str
    source_refs: List[str]

class ReviewerAgentOutput(BaseModel):
    findings: List[RefinedFinding]
