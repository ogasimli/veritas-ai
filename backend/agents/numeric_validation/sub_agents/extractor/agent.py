"""Extractor sub-agent definition."""
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from .schema import ExtractorAgentOutput
from . import prompt

extractor_agent = LlmAgent(
    name="ExtractorAgent",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="extractor_output",
    output_schema=ExtractorAgentOutput,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_level="high")
    ),
)
