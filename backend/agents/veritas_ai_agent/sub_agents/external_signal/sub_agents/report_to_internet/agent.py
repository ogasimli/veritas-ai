"""Report-to-internet verification agent with Deep Research."""
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai.types import GenerateContentConfig
from ...deep_research_client import DeepResearchClient
from veritas_ai_agent.app_utils.error_handler import default_model_error_handler
from . import prompt
from .schema import ReportToInternetOutput

# Initialize Deep Research client (singleton pattern)
deep_research_client = DeepResearchClient()


async def verify_claims_tool(claims_json: str) -> str:
    """
    Verify financial statement claims using Deep Research.

    Args:
        claims_json: JSON string with extracted claims to verify

    Returns:
        Deep Research verification results with status, evidence, sources
    """
    verification_prompt = f"""
Verify these claims from a financial statement using publicly available information:

{claims_json}

For each claim:

1. **Search authoritative sources:**
   - Official registries (Delaware Division of Corporations, SEC EDGAR, etc.)
   - SEC filings (10-K, 8-K, proxy statements)
   - Company official websites and press releases
   - Regulatory databases
   - Reputable business news (for acquisitions, partnerships, awards)

2. **Determine verification status:**
   - **VERIFIED**: Claim matches public sources (exact or substantially accurate)
   - **CONTRADICTED**: Public sources conflict with the claim
   - **CANNOT_VERIFY**: No authoritative sources found to confirm or deny

3. **Cite sources with URLs:**
   - Provide specific URLs from search results
   - Prefer official/primary sources over secondary sources

4. **Note discrepancies:**
   - If dates are slightly off (e.g., claim says Jan 15, source says Jan 14): still VERIFIED but note discrepancy
   - If wording differs but meaning is same: VERIFIED with note
   - If substantial conflict: CONTRADICTED with details

**Output format:**
For each claim, provide:
- Claim text
- Verification status (VERIFIED/CONTRADICTED/CANNOT_VERIFY)
- Evidence summary (what was found)
- Source URLs (list of supporting links)
- Discrepancy notes (if any differences detected)

Structure output as JSON-like format matching the ClaimVerification schema.
"""

    result = await deep_research_client.run_research(
        query=verification_prompt,
        timeout_minutes=20
    )

    if result["status"] != "completed":
        return f"ERROR: Deep Research {result['status']} - {result['error']}"

    return result["result"]


# Create LlmAgent with Deep Research verification tool
report_to_internet_agent = LlmAgent(
    name="report_to_internet",
    model="gemini-3-flash-preview",  # Lightweight coordinator
    instruction=prompt.INSTRUCTION,
    tools=[FunctionTool(verify_claims_tool)],
    output_key="report_to_internet_findings",
    output_schema=ReportToInternetOutput,
    on_model_error_callback=default_model_error_handler,
)
