"""MultiPassRefinementAgent: N parallel chains x M sequential passes → aggregation.

Uses ADK's LoopAgent for the M sequential passes within each chain.
"""

import json
import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from veritas_ai_agent.shared.error_handler import default_model_error_handler

from .config import MultiPassRefinementConfig

logger = logging.getLogger(__name__)


class MultiPassRefinementAgent(BaseAgent):
    """Reusable agent that runs NxM LLM passes to maximize finding coverage.

    Architecture:
    - N parallel chains run independently (parallel branches explore different paths)
    - Each chain is a SequentialAgent with M passes (later passes see prior findings)
    - Final aggregator deduplicates all findings across all chains

    Parameters
    ----------
    name : str
        Agent name (e.g., "LogicConsistencyDetector")
    config : MultiPassRefinementConfig
        Complete configuration including domain logic and runtime parameters
    output_key : str
        State key to write final aggregated output
    """

    config: MultiPassRefinementConfig | None = None
    output_key: str | None = None
    parallel_agent: ParallelAgent | None = None
    aggregator_agent: LlmAgent | None = None

    def __init__(
        self,
        name: str,
        config: MultiPassRefinementConfig,
        output_key: str | None = None,
    ):
        output_key = output_key or f"{name.lower()}_output"

        # --- Build Static Agent Graph ---
        # Note: We must create these locally before super().__init__ because
        # Pydantic models require __init__ to set fields.
        chain_agents = []
        for chain_idx in range(config.n_parallel_chains):
            chain_sequence = self._create_chain_sequence(name, config, chain_idx)
            chain_agents.append(chain_sequence)

        parallel_agent = ParallelAgent(
            name=f"{name}_ParallelChains",
            sub_agents=chain_agents,
        )

        aggregator_agent = self._create_aggregator(name, config, output_key)

        # Initialize BaseAgent with all sub-agents and config
        super().__init__(
            name=name,
            sub_agents=[parallel_agent, aggregator_agent],
        )
        self.config = config
        self.output_key = output_key
        self.parallel_agent = parallel_agent
        self.aggregator_agent = aggregator_agent

    @property
    def _internal_findings_key(self) -> str:
        return f"{self.name}_all_findings"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        # Ensure agents are initialized
        assert self.parallel_agent is not None
        assert self.aggregator_agent is not None

        # --- Phase 1: Run N parallel chains ---
        async for event in self.parallel_agent.run_async(ctx):
            yield event

        # --- Phase 2: Collect all findings from all chains ---
        assert self.config is not None
        all_findings: list[dict] = []
        for chain_idx in range(self.config.n_parallel_chains):
            key = f"{self.name}_chain_{chain_idx}_accumulated_findings"
            chain_findings = state.get(key, [])
            all_findings.extend(chain_findings)

        # Store findings in state so the Aggregator's dynamic instruction can read them
        state[self._internal_findings_key] = all_findings

        logger.info(
            "%s: collected %d total findings from %d chains x %d passes",
            self.name,
            len(all_findings),
            self.config.n_parallel_chains,
            self.config.m_sequential_passes,
        )

        # --- Phase 3: Aggregate/deduplicate ---
        async for event in self.aggregator_agent.run_async(ctx):
            yield event

    def _create_chain_sequence(
        self, agent_name: str, config: MultiPassRefinementConfig, chain_idx: int
    ) -> SequentialAgent:
        """Create a SequentialAgent that runs M sequential passes for one chain."""
        accumulated_key = f"{agent_name}_chain_{chain_idx}_accumulated_findings"
        sub_agents = []

        def before_sequence_callback(callback_context: CallbackContext) -> None:
            """Initialize accumulated findings list for this chain."""
            callback_context.state.setdefault(accumulated_key, [])

        # Build LlmAgent config (shared across passes)
        chain_config = config.chain_agent_config
        model = chain_config.model

        for pass_idx in range(config.m_sequential_passes):
            pass_output_key = f"chain_{chain_idx}_pass_{pass_idx}_output"

            # Create closure for this specific pass
            def make_after_pass_callback(current_pass_key: str):
                def after_pass_callback(callback_context: CallbackContext) -> None:
                    """Append findings from current pass to accumulated list."""
                    # Call user's callback first if provided
                    if chain_config.after_agent_callback:
                        chain_config.after_agent_callback(callback_context)

                    # Then accumulate findings (required for multi-pass pattern)
                    output = callback_context.state.get(current_pass_key)
                    if not output:
                        return
                    if hasattr(output, "model_dump"):
                        output = output.model_dump()
                    new_findings = config.extract_findings(output)
                    # Explicitly set the key back to trigger state update events by creating a new list
                    # (In-place modification might not trigger the state change listener)
                    current_findings = list(callback_context.state[accumulated_key])
                    current_findings.extend(new_findings)
                    callback_context.state[accumulated_key] = current_findings
                    logger.debug(
                        "%s chain %d pass %d: accumulated %d findings",
                        agent_name,
                        chain_idx,
                        pass_idx,
                        len(callback_context.state[accumulated_key]),
                    )

                return after_pass_callback

            # Build LlmAgent kwargs
            agent_kwargs = {
                "name": f"{agent_name}_Chain{chain_idx}_Pass{pass_idx}",
                "model": model,
                "instruction": chain_config.get_instruction(chain_idx),
                "output_schema": chain_config.output_schema,
                "output_key": pass_output_key,
                "after_agent_callback": make_after_pass_callback(pass_output_key),
                "planner": chain_config.planner,
                "generate_content_config": chain_config.generate_content_config,
                "before_agent_callback": chain_config.before_agent_callback,
                "on_model_error_callback": chain_config.on_model_error_callback,
                "before_model_callback": chain_config.before_model_callback,
                "after_model_callback": chain_config.after_model_callback,
                "before_tool_callback": chain_config.before_tool_callback,
                "after_tool_callback": chain_config.after_tool_callback,
                "tools": chain_config.tools or [],
                "code_executor": chain_config.code_executor,
            }

            pass_agent = LlmAgent(**agent_kwargs)
            sub_agents.append(pass_agent)

        return SequentialAgent(
            name=f"{agent_name}_Chain_{chain_idx}",
            sub_agents=sub_agents,
            before_agent_callback=before_sequence_callback,
        )

    def _create_aggregator(
        self, agent_name: str, config: MultiPassRefinementConfig, output_key: str
    ) -> LlmAgent:
        """Create LLM-based aggregator with dynamic instruction."""
        # Build aggregator config
        agg_config = config.aggregator_config
        model = agg_config.model
        planner = agg_config.planner
        generate_config = agg_config.generate_content_config

        # Dynamic instruction provider
        def aggregator_instruction_provider(ctx: InvocationContext) -> str:
            findings = ctx.session.state.get(self._internal_findings_key, [])
            all_findings_json = json.dumps(findings, indent=2)
            return agg_config.get_instruction(all_findings_json)

        # Build LlmAgent kwargs
        agent_kwargs = {
            "name": f"{agent_name}Aggregator",
            "model": model,
            "instruction": aggregator_instruction_provider,
            "output_schema": agg_config.output_schema,
            "output_key": output_key,
            "planner": planner,
            "generate_content_config": generate_config,
            "before_agent_callback": agg_config.before_agent_callback,
            "after_agent_callback": agg_config.after_agent_callback,
            "on_model_error_callback": agg_config.on_model_error_callback
            or default_model_error_handler,
            "before_model_callback": agg_config.before_model_callback,
            "after_model_callback": agg_config.after_model_callback,
            "before_tool_callback": agg_config.before_tool_callback,
            "after_tool_callback": agg_config.after_tool_callback,
            "tools": agg_config.tools or [],
            "code_executor": agg_config.code_executor,
        }

        return LlmAgent(**agent_kwargs)
