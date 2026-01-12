from typing import List
from pydantic import BaseModel, Field

class VerificationCheck(BaseModel):
    fsli_name: str = Field(description="Name of the Financial Statement Line Item being verified")
    check_type: str = Field(description="Type of mathematical check performed, e.g., 'in_table_sum' or 'cross_table_consistency'")
    description: str = Field(description="Human-readable description of what specifically was checked")
    expected_value: float = Field(description="The value expected based on calculations or other table references")
    actual_value: float = Field(description="The actual value found in the document for this FSLI")
    check_passed: bool = Field(description="Whether the mathematical check passed (True) or failed (False)")
    source_refs: List[str] = Field(description="References to the locations in the document used for this check, e.g., ['Table 4, Row 12', 'Note 5']")
    code_executed: str = Field(description="The Python code that was executed to perform the verification")

class VerifierAgentOutput(BaseModel):
    checks: List[VerificationCheck]
