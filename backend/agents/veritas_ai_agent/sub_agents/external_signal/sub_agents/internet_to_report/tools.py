"""Tools for internet-to-report verification agent."""

from ...deep_research_client import DeepResearchClient
from . import prompt

# Initialize Deep Research client (singleton pattern)
deep_research_client = DeepResearchClient()


async def search_external_signals_tool(
    company_profile: dict, research_window: dict
) -> str:
    """
    Tool that uses Deep Research to find external signals about company.

    This tool accepts the full company profile and research window extracted
    from the financial statement, allowing Deep Research to conduct more
    targeted and comprehensive research.

    Args:
        company_profile: Dictionary containing company identification and scope:
            - legal_name: str
            - alternative_names: list[str]
            - jurisdiction: str
            - subsidiaries: list[str]
            - key_management: list[str]
            - material_counterparties: list[str]
            - industry_sector: str
            - business_context: str
            (and other fields from CompanyProfile schema)

        research_window: Dictionary containing temporal scope:
            - fiscal_year: str
            - reporting_date: str
            - fs_issue_date: str | None
            - subsequent_period_start: str
            - subsequent_period_end: str
            - assumption_used: bool

    Returns:
        Deep Research findings about external risk signals in JSON format
    """
    research_query = prompt.get_deep_research_instruction(
        company_profile, research_window
    )

    result = await deep_research_client.run_research(
        query=research_query, timeout_minutes=20
    )

    if result["status"] != "completed":
        return f"ERROR: Deep Research {result['status']} - {result['error']}"

    return result["result"]
