"""Tools for internet-to-report verification agent."""

import json

from veritas_ai_agent.sub_agents.audit_orchestrator.sub_agents.external_signal.deep_research_client import (
    DeepResearchClient,
)

from . import prompt

# Initialize Deep Research client (singleton pattern)
deep_research_client = DeepResearchClient()


async def search_external_signals_tool(
    company_profile_json: str, research_window_json: str
) -> str:
    """
    Tool that uses Deep Research to find external signals about company.

    Args:
        company_profile_json: JSON string with company identification (legal_name, jurisdiction, subsidiaries, key_management, etc.)
        research_window_json: JSON string with temporal scope (fiscal_year, reporting_date, subsequent_period_end, etc.)

    Returns:
        Deep Research findings about external risk signals in JSON format
    """
    # Parse JSON strings
    try:
        company_profile = json.loads(company_profile_json)
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON for company_profile: {e}"

    try:
        research_window = json.loads(research_window_json)
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON for research_window: {e}"

    research_query = prompt.get_deep_research_instruction(
        company_profile, research_window
    )

    result = await deep_research_client.run_research(
        query=research_query, timeout_minutes=20
    )

    if result["status"] != "completed":
        return f"ERROR: Deep Research {result['status']} - {result['error']}"

    return result["result"]
