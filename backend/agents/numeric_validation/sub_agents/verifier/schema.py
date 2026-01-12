from typing import List
from pydantic import BaseModel

class VerificationCheck(BaseModel):
    fsli_name: str
    check_type: str              # "in_table_sum" | "cross_table_consistency"
    description: str             # What was checked
    expected_value: float
    actual_value: float
    result: str                  # "pass" | "fail"
    source_refs: List[str]       # ["Table 4, Row 12", "Note 5"]
    code_executed: str           # Python code used for verification

class VerifierAgentOutput(BaseModel):
    checks: List[VerificationCheck]
