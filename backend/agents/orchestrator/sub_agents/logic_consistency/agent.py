"""Logic Consistency Agent - detects semantic contradictions in financial statements."""
from google.adk.agents import LlmAgent

from . import prompt
from .schema import LogicConsistencyOutput

logic_consistency_agent = LlmAgent(
    name="logic_consistency",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="logic_consistency_output",
    output_schema=LogicConsistencyOutput,
)
