"""Cross-table detector factory — creates statement-specific detector agents."""

from collections.abc import Callable

from google.adk.agents.invocation_context import InvocationContext
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

from .prompt import get_aggregator_instruction
from .schema import CrossTableDetectorOutput


def create_cross_table_detector(
    agent_name: str,
    output_key: str,
    first_pass_instruction: str,
    refinement_instruction: str,
    n_parallel_chains: int = 1,
    m_sequential_passes: int = 3,
) -> MultiPassRefinementAgent:
    """Factory function to create a cross-table inconsistency detector.

    Parameters
    ----------
    agent_name : str
        Name of the agent (e.g., "BalanceSheetCrossTableInconsistencyDetector")
    output_key : str
        State key to write final output (e.g., "balance_sheet_cross_table_inconsistency_detector_output")
    first_pass_instruction : str
        Prompt for the first pass (should contain {extracted_tables} placeholder)
    refinement_instruction : str
        Prompt for refinement passes (should contain {AgentName_chain_CHAIN_IDX_accumulated_findings} and {extracted_tables})
    n_parallel_chains : int
        Number of parallel chains to run (default: 1)
    m_sequential_passes : int
        Number of sequential passes per chain (default: 3)

    Returns
    -------
    MultiPassRefinementAgent
        Configured detector agent
    """

    def extract_findings(output: dict) -> list[dict]:
        findings = output.get("findings", [])
        return [f.model_dump() if hasattr(f, "model_dump") else f for f in findings]

    def get_pass_instruction(
        chain_idx: int,
    ) -> Callable[[InvocationContext], str]:
        findings_key = f"{agent_name}_chain_{chain_idx}_accumulated_findings"

        def instruction_provider(ctx: InvocationContext) -> str:
            findings = ctx.session.state.get(findings_key, [])
            if not findings:
                return first_pass_instruction
            return refinement_instruction.replace("CHAIN_IDX", str(chain_idx))

        return instruction_provider

    planner = BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, thinking_level="high"
        )
    )
    generate_content_config = types.GenerateContentConfig(
        http_options=types.HttpOptions(retry_options=get_default_retry_config())
    )

    chain_config = MultiPassRefinementLlmAgentConfig(
        output_schema=CrossTableDetectorOutput,
        get_instruction=get_pass_instruction,
        on_model_error_callback=default_model_error_handler,
        planner=planner,
        generate_content_config=generate_content_config,
        code_executor=BuiltInCodeExecutor(),
    )

    aggregator_config = MultiPassRefinementLlmAgentConfig(
        output_schema=CrossTableDetectorOutput,
        get_instruction=get_aggregator_instruction,
        on_model_error_callback=default_model_error_handler,
        planner=planner,
        generate_content_config=generate_content_config,
    )

    config = MultiPassRefinementConfig(
        chain_agent_config=chain_config,
        aggregator_config=aggregator_config,
        extract_findings=extract_findings,
        n_parallel_chains=n_parallel_chains,
        m_sequential_passes=m_sequential_passes,
    )

    return MultiPassRefinementAgent(
        name=agent_name,
        config=config,
        output_key=output_key,
    )
