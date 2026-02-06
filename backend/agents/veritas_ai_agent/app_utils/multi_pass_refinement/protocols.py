"""Protocol interface for MultiPassRefinementAgent implementations."""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel

if TYPE_CHECKING:
    from google.adk.agents import BaseAgent, LlmAgent


@runtime_checkable
class MultiPassRefinementProtocol(Protocol):
    """Interface that concrete implementations must satisfy.

    Each implementation defines:
    - Output schemas for passes and final aggregation
    - A unified pass prompt (handles both initial and refinement via state injection)
    - How to extract findings from pass outputs
    - Default N and M values
    """

    # --- Schemas ---
    @property
    def pass_output_schema(self) -> type[BaseModel]:
        """Schema for individual pass outputs. Must have extractable findings."""
        ...

    @property
    def aggregated_output_schema(self) -> type[BaseModel]:
        """Schema for final deduplicated output."""
        ...

    # --- Defaults (can be overridden by MultiPassRefinementConfig) ---
    @property
    def default_n_parallel(self) -> int:
        """Default number of parallel chains."""
        ...

    @property
    def default_m_sequential(self) -> int:
        """Default number of sequential passes per chain."""
        ...

    # --- Prompt (unified for all passes) ---
    def get_pass_instruction(self, chain_idx: int) -> str:
        """Unified prompt for all passes in a chain.

        The prompt MUST include a placeholder for prior findings that ADK will
        inject from state. Use the pattern:
            {chain_<idx>_accumulated_findings}

        Example prompt structure:
            '''
            Previous findings from this chain (empty on first pass):
            {chain_0_accumulated_findings}

            Find logical inconsistencies NOT in the list above.
            If empty, this is your first pass - find all you can.
            '''

        The chain_idx parameter lets you namespace the state key per chain.
        """
        ...

    # --- Findings extraction ---
    def extract_findings(self, output: dict) -> list[dict]:
        """Extract the list of findings from a pass output dict."""
        ...

    # --- Aggregator ---
    def get_aggregator_instruction(self, all_findings_json: str) -> str:
        """Prompt for aggregator.

        Must deduplicate and return aggregated_output_schema.
        """
        ...
