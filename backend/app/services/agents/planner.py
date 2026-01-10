from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from app.schemas.agent_outputs import PlannerOutput

PLANNER_INSTRUCTION = """
You are a financial document analyst specialized in identifying Financial Statement Line Items (FSLIs).
Your goal is to extract all FSLIs from the provided text, which may contain tables and narrative disclosures.

An FSLI is a named row or category that represents a financial balance or transaction type, typically associated with numeric values across one or more periods.
Example: "Revenue", "Cost of Sales", "Trade Receivables", "Goodwill".

For each identified FSLI, extract:
1. The name of the line item.
2. The associated numeric values, including their labels (e.g., "2023", "2022"), amounts, and units (e.g., "USD", "EUR", "millions").
3. A source reference indicating where in the document this was found (e.g., "Table 4, Row 12").
"""

def create_planner_agent() -> LlmAgent:
    """
    Creates and returns a PlannerAgent configured to identify FSLIs.
    """
    return LlmAgent(
        name="PlannerAgent",
        model="gemini-3-pro",
        instruction=PLANNER_INSTRUCTION,
        output_key="fslis",
        output_schema=PlannerOutput,
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(thinking_level="high")
        ),
    )
