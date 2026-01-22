"""Internet-to-report verification agent with Deep Research."""
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai.types import GenerateContentConfig
from ...deep_research_client import DeepResearchClient
from . import prompt
from .schema import InternetToReportOutput

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
    research_query = f"""
Research external signals about {company_name} during fiscal year {fiscal_year}.

Search for three types of signals:

1. **News articles** - Major company developments, events, controversies
2. **Litigation and legal proceedings** - Lawsuits, regulatory actions, legal issues
3. **Financial distress signals** - Credit downgrades, bankruptcy filings, liquidity concerns

Focus on reporting period {fiscal_year} and few months prior for context.

Use only reputable sources:
- Official filings (SEC, regulatory agencies)
- Major news outlets (Wall Street Journal, Financial Times, Reuters, Bloomberg)
- Regulatory websites
- Credit rating agencies

For each signal found, provide:
- Signal type (news/litigation/financial_distress)
- Summary (2-3 sentences explaining what happened)
- Source URL and publication date
- Any potential contradictions with typical financial statement claims

If no significant signals are found, explicitly state that.
"""

    result = await deep_research_client.run_research(
        query=research_query,
        timeout_minutes=20
    )

    if result["status"] != "completed":
        return f"ERROR: Deep Research {result['status']} - {result['error']}"

    return result["result"]


# Create LlmAgent with Deep Research tool integration
internet_to_report_agent = LlmAgent(
    name="internet_to_report",
    model="gemini-3-flash-preview",  # Lightweight coordinator
    instruction=prompt.INSTRUCTION,
    tools=[FunctionTool(search_external_signals_tool)],
    output_key="internet_to_report_findings",
    output_schema=InternetToReportOutput,
)
