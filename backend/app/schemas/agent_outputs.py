from pydantic import BaseModel, Field
from typing import List

class FSLIValue(BaseModel):
    label: str = Field(description="Label for the value, typically a year or period (e.g., '2023', 'Q3').")
    amount: float = Field(description="The numeric value of the line item for this period.")
    unit: str = Field(description="The currency and scale (e.g., 'USD millions', 'EUR').")

class FSLI(BaseModel):
    name: str = Field(description="Name of the Financial Statement Line Item (e.g., 'Revenue', 'Net Income').")
    values: List[FSLIValue] = Field(description="List of numeric values associated with this line item across different periods.")
    source_ref: str = Field(description="Reference to the source in the document (e.g., 'Table 4, Row 12').")

class PlannerOutput(BaseModel):
    fslis: List[FSLI] = Field(description="List of identified Financial Statement Line Items.")
