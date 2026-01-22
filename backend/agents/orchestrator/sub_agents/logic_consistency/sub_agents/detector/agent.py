from google.adk.agents import LlmAgent
from agents.common.error_handler import default_model_error_handler
from . import prompt
from .schema import DetectorAgentOutput

detector_agent = LlmAgent(
    name="LogicDetector",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="detector_output",
    output_schema=DetectorAgentOutput,
    on_model_error_callback=default_model_error_handler,
)
