"""Scanner sub-agent definition."""
from google.adk.agents import LlmAgent
from .schema import ScannerAgentOutput
from . import prompt
from agents.common.error_handler import default_model_error_handler

scanner_agent = LlmAgent(
    name="ScannerAgent",
    model="gemini-3-flash-preview",
    instruction=prompt.INSTRUCTION,
    output_key="scanner_output",
    output_schema=ScannerAgentOutput,
    on_model_error_callback=default_model_error_handler,
)
