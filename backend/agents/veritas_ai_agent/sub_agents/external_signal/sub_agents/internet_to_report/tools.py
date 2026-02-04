"""Tools for internet-to-report verification agent."""

from ...deep_research_client import DeepResearchClient
from . import prompt

# Initialize Deep Research client (singleton pattern)
deep_research_client = DeepResearchClient()


async def search_external_signals_tool(company_name: str, fiscal_year: str) -> str:
    """
    Tool that uses Deep Research to find external signals about company.

    Args:
        company_name: Legal entity name from financial statement
        fiscal_year: Reporting period year

    Returns:
        Deep Research findings about external risk signals
    """
    research_query = prompt.get_deep_research_instruction(company_name, fiscal_year)

    result = await deep_research_client.run_research(
        query=research_query, timeout_minutes=20
    )

    if result["status"] != "completed":
        return f"ERROR: Deep Research {result['status']} - {result['error']}"

    return result["result"]
