"""Report-to-internet verification agent with Deep Research."""

from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.adk.tools import FunctionTool
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.model_name_config import GEMINI_PRO

from . import prompt
from .schema import ExternalSignalReportToInternetOutput
from .tools import verify_claims_tool

# Create LlmAgent with Deep Research verification tool
report_to_internet_agent = LlmAgent(
    name="ExternalSignalReportToInternet",
    model=GEMINI_PRO,
    instruction=prompt.INSTRUCTION,
    tools=[FunctionTool(verify_claims_tool)],
    output_key="external_signal_report_to_internet_output",
    output_schema=ExternalSignalReportToInternetOutput,
    on_model_error_callback=default_model_error_handler,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level="high"
        )
    ),
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    ),
)
