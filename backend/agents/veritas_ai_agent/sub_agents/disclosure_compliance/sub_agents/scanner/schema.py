from pydantic import BaseModel, Field
from typing import List

class ScannerAgentOutput(BaseModel):
    """Output schema for Scanner agent."""
    applicable_standards: List[str] = Field(
        default_factory=list,
        description="List of IFRS/IAS standard codes applicable to this financial statement (e.g., ['IAS 1', 'IFRS 15'])"
    )
