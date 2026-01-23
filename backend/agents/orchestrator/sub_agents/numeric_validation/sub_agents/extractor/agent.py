"""Extractor sub-agent definition."""
from google.adk.agents import LlmAgent
from .schema import ExtractorAgentOutput
from . import prompt
from agents.common.error_handler import default_model_error_handler

extractor_agent = LlmAgent(
    name="ExtractorAgent",
    model="gemini-3-flash-preview",
    instruction=prompt.INSTRUCTION,
    output_key="extractor_output",
    output_schema=ExtractorAgentOutput,
    on_model_error_callback=default_model_error_handler,
)
