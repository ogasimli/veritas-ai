"""Tools for report-to-internet verification agent."""

from ...deep_research_client import DeepResearchClient
from . import prompt
from .schema import ExternalSignalVerifiableClaim

# Initialize Deep Research client (singleton pattern)
deep_research_client = DeepResearchClient()


async def verify_claims_tool(claims: list[ExternalSignalVerifiableClaim]) -> str:
    """
    Verify financial statement claims using Deep Research.

    Args:
        claims: List of extracted claims to verify

    Returns:
        Deep Research verification results with status, evidence, sources
    """

    def _format_claims(claims_input: list[ExternalSignalVerifiableClaim]) -> str:
        # Normalize claims to objects if they are passed as dicts
        # (ADK/Framework behavior might pass dicts even with type hints)
        normalized_claims = []
        for c in claims_input:
            if isinstance(c, dict):
                normalized_claims.append(ExternalSignalVerifiableClaim(**c))
            else:
                normalized_claims.append(c)

        # Convert claims to a readable format for the research prompt
        return "\n".join(
            [
                f"- [{c.claim_type}] {c.claim_text} (Query: {c.verification_query})"
                for c in normalized_claims
            ]
        )

    claims_formatted = _format_claims(claims)

    verification_prompt = prompt.get_deep_research_instruction(claims_formatted)

    result = await deep_research_client.run_research(
        query=verification_prompt, timeout_minutes=20
    )

    if result["status"] != "completed":
        return f"ERROR: Deep Research {result['status']} - {result['error']}"

    return result["result"]
