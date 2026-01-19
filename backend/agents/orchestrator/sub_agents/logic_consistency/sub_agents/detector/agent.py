from google.adk.agents import LlmAgent
from . import prompt
from .schema import DetectorAgentOutput

detector_agent = LlmAgent(
    name="LogicDetector",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="detector_output",
    output_schema=DetectorAgentOutput,
)
