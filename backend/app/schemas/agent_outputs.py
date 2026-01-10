from pydantic import BaseModel
from typing import List

class FSLIValue(BaseModel):
    label: str
    amount: float
    unit: str

class FSLI(BaseModel):
    name: str
    values: List[FSLIValue]
    source_ref: str

class PlannerOutput(BaseModel):
    fslis: List[FSLI]
