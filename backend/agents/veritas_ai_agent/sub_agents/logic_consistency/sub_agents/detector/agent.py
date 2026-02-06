from google.adk.agents import LlmAgent
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config

from . import prompt
from .schema import LogicConsistencyDetectorOutput

detector_agent = LlmAgent(
    name="LogicConsistencyDetector",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="logic_consistency_detector_output",
    output_schema=LogicConsistencyDetectorOutput,
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
