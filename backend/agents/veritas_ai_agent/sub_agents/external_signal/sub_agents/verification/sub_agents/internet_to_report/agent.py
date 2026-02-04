"""Internet-to-report verification agent with Deep Research."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from veritas_ai_agent.app_utils.llm_config import get_default_retry_config

from . import prompt
from .schema import ExternalSignalInternetToReportOutput
from .tools import search_external_signals_tool

# Create LlmAgent with Deep Research tool integration
internet_to_report_agent = LlmAgent(
    name="ExternalSignalInternetToReport",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    tools=[FunctionTool(search_external_signals_tool)],
    output_key="external_signal_internet_to_report_output",
    output_schema=ExternalSignalInternetToReportOutput,
    on_model_error_callback=default_model_error_handler,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
