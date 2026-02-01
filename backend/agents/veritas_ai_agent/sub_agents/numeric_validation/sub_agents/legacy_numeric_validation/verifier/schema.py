from enum import Enum

from pydantic import BaseModel, Field


class LegacyNumericCheckType(str, Enum):
    IN_TABLE_SUM = "in_table_sum"
    CROSS_TABLE_CONSISTENCY = "cross_table_consistency"


class LegacyNumericVerificationCheck(BaseModel):
    fsli_name: str = Field(
        description="Name of the Financial Statement Line Item being verified"
    )
    check_type: LegacyNumericCheckType = Field(
        description="Type of mathematical check performed"
    )
    description: str = Field(
        description="Human-readable description of what specifically was checked"
    )
    expected_value: float = Field(
        description="The value expected based on calculations or other table references"
    )
    actual_value: float = Field(
        description="The actual value found in the document for this FSLI"
    )
    check_passed: bool = Field(
        description="Whether the mathematical check passed (True) or failed (False)"
    )
    source_refs: list[str] = Field(
        description="References to the locations in the document used for this check, e.g., ['Table 4, Row 12', 'Note 5']"
    )
    code_executed: str = Field(
        description="The Python code that was executed to perform the verification"
    )


from veritas_ai_agent.schemas import BaseAgentOutput


class LegacyNumericVerifierOutput(BaseAgentOutput):
    checks: list[LegacyNumericVerificationCheck] = Field(
        default_factory=list,
        description="List of mathematical verification checks performed for this FSLI",
    )
