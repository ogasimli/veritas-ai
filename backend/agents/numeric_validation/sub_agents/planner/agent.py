"""Planner sub-agent definition."""
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from .schema import PlannerAgentAgentOutput
from . import prompt

planner_agent = LlmAgent(
    name="PlannerAgent",
    model="gemini-3-pro-preview",
    instruction=prompt.INSTRUCTION,
    output_key="planner_agent_output",
    output_schema=PlannerAgentAgentOutput,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_level="high")
    ),
)
