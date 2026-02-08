"""Tools for report-to-internet verification agent."""

import json

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.deep_research_client import (
    DeepResearchClient,
)

from . import prompt
from .schema import ExternalSignalVerifiableClaim

# Initialize Deep Research client (singleton pattern)
deep_research_client = DeepResearchClient()


async def verify_claims_tool(claims_json: str) -> str:
    """
    Verify financial statement claims using Deep Research.

    Args:
        claims_json: JSON string containing list of claims to verify.
            Each claim should have: claim_text, claim_category, verification_query, entity_subject

    Returns:
        Deep Research verification results with status, evidence, sources
    """
    # Parse JSON string to list of dicts
    try:
        claims_list = json.loads(claims_json)
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON provided for claims: {e}"

    def _format_claims(claims_input: list) -> str:
        # Normalize claims to objects if they are passed as dicts
        normalized_claims = []
        for c in claims_input:
            if isinstance(c, dict):
                normalized_claims.append(ExternalSignalVerifiableClaim(**c))
            else:
                normalized_claims.append(c)

        # Convert claims to a readable format for the research prompt
        return "\n".join(
            [
                f"- [{c.claim_category}] {c.claim_text} (Query: {c.verification_query})"
                for c in normalized_claims
            ]
        )

    claims_formatted = _format_claims(claims_list)

    verification_prompt = prompt.get_deep_research_instruction(claims_formatted)

    result = await deep_research_client.run_research(
        query=verification_prompt, timeout_minutes=10
    )

    if result["status"] != "completed":
        return f"ERROR: Deep Research {result['status']} - {result['error']}"

    return result["result"]
