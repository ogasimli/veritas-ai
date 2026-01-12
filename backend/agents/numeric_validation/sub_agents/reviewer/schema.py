from typing import List
from pydantic import BaseModel

class Finding(BaseModel):
    fsli_name: str
    summary: str                 # Short human-readable summary
    severity: str                # "high" | "medium" | "low"
    expected_value: float
    actual_value: float
    discrepancy: float           # Absolute difference
    source_refs: List[str]       # ["Table 4, Row 12", "Note 5"]

class ReviewerAgentOutput(BaseModel):
    findings: List[Finding]
