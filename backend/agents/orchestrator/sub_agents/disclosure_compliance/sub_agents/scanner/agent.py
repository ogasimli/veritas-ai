"""Scanner sub-agent definition."""
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from .schema import ScannerAgentOutput
from . import prompt
from agents.common.error_handler import default_model_error_handler

scanner_agent = LlmAgent(
    name="ScannerAgent",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="scanner_output",
    output_schema=ScannerAgentOutput,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_level="high")
    ),
    on_model_error_callback=default_model_error_handler,
)
