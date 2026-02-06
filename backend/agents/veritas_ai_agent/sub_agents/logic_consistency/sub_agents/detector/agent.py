"""Logic Consistency Detector - uses multi-pass refinement to find contradictions.

Runs N parallel chains x M sequential passes to maximize finding coverage.
Each chain explores independently, with later passes finding issues missed earlier.
"""

from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.planners.built_in_planner import BuiltInPlanner
from google.genai import types

from veritas_ai_agent.shared.error_handler import default_model_error_handler
from veritas_ai_agent.shared.llm_config import get_default_retry_config
from veritas_ai_agent.shared.multi_pass_refinement import MultiPassRefinementAgent
from veritas_ai_agent.shared.multi_pass_refinement.config import (
    MultiPassRefinementConfig,
    MultiPassRefinementLlmAgentConfig,
)

from . import prompt
from .schema import LogicConsistencyDetectorOutput


def _create_config() -> MultiPassRefinementConfig:
    """Create the MultiPassRefinementConfig for the logic consistency detector."""

    def extract_findings_wrapper(output: dict) -> list[dict]:
        """Extract the list of findings from a pass output dict."""
        findings = output.get("findings", [])
        # Convert to dict if they're Pydantic models
        return [f.model_dump() if hasattr(f, "model_dump") else f for f in findings]

    def get_pass_instruction_wrapper(chain_idx: int) -> str:
        """Unified prompt for all passes in a chain."""
        return prompt.PASS_INSTRUCTION.replace("CHAIN_IDX", str(chain_idx))

    def get_aggregator_instruction_wrapper(all_findings_json: str) -> str:
        """Prompt for default aggregator."""
        return prompt.get_aggregator_instruction(all_findings_json)

    # Common planner and gen config
    planner = BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level="high"
        )
    )
    generate_content_config = types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    )

    # Configure the chain agents (the detectors)
    chain_config = MultiPassRefinementLlmAgentConfig(
        output_schema=LogicConsistencyDetectorOutput,
        get_instruction=get_pass_instruction_wrapper,
        on_model_error_callback=default_model_error_handler,
        planner=planner,
        generate_content_config=generate_content_config,
        code_executor=BuiltInCodeExecutor(),
    )

    # Configure the aggregator agent
    aggregator_config = MultiPassRefinementLlmAgentConfig(
        output_schema=LogicConsistencyDetectorOutput,
        get_instruction=get_aggregator_instruction_wrapper,
        on_model_error_callback=default_model_error_handler,
        planner=planner,
        generate_content_config=generate_content_config,
    )

    return MultiPassRefinementConfig(
        chain_agent_config=chain_config,
        aggregator_config=aggregator_config,
        extract_findings=extract_findings_wrapper,
        n_parallel_chains=3,
        m_sequential_passes=3,
    )


detector_agent = MultiPassRefinementAgent(
    name="LogicConsistencyDetector",
    config=_create_config(),
    output_key="logic_consistency_detector_output",
)
