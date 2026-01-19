# Phase 6: External Signal - Research

**Researched:** 2026-01-19
**Domain:** Gemini google_search tool API and Google ADK integration
**Confidence:** HIGH

<research_summary>
## Summary

Researched the Gemini google_search tool for building an external signal agent that searches news, litigation, and financial distress signals. The standard approach uses Google ADK's LlmAgent with the google_search built-in tool, which automatically handles search query generation, execution, and result synthesis.

Key finding: The google_search tool has a critical "one tool per agent" restriction in ADK - it cannot be combined with other tools like code_executor in a single agent. The workaround is multi-agent architecture (separate search agent coordinated by root orchestrator) or using `bypass_multi_tools_limit=True` in Python ADK.

The model autonomously determines when to search, generates multiple queries as needed, and returns grounded responses with structured metadata (search queries, source URLs, and citation indices). Results are grounded in real-time web data, reducing hallucinations and providing current information for news/litigation searches.

**Primary recommendation:** Create standalone LlmAgent with google_search tool only (no code_executor), let model generate queries based on prompt context (company name + year), process groundingMetadata for citations, and verify critical findings against source URLs.
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google.adk.agents.LlmAgent | Latest | Agent wrapper for Gemini | Native ADK integration for google_search |
| Gemini 2.5/3.0 models | 2.5-flash, 3-pro | LLM with google_search | Only Gemini 2+ supports google_search tool |
| google_search tool | Built-in | Web search grounding | Official Gemini API tool, handles search autonomously |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| AgentTool | ADK built-in | Wrap agents as tools | Multi-agent coordination when mixing search with other tools |
| types.GoogleSearch() | Gemini API | Low-level tool config | Direct API calls (non-ADK) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| google_search | Custom web scraping | google_search is grounded, cited, Terms-compliant; scraping violates TOS and lacks grounding |
| Gemini 2.5/3.0 | google_search_retrieval (deprecated) | Old tool for Gemini 1.x, use google_search for current models |

**Installation:**
```bash
# google_search is built-in to Gemini API, no separate installation
# Included when using Google ADK:
pip install google.adk
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
backend/agents/orchestrator/sub_agents/
├── external_signal/
│   ├── agent.py          # LlmAgent with google_search tool
│   ├── prompt.py         # Instructions for search + analysis
│   ├── schema.py         # Output schema (findings list)
│   └── __init__.py
```

### Pattern 1: Standalone Search Agent
**What:** LlmAgent with google_search as sole tool (one-tool restriction)
**When to use:** Any search-based agent task
**Example:**
```python
# Source: ADK docs - google.github.io/adk-docs/tools/gemini-api/google-search/
from google.adk.agents import LlmAgent
from google.adk.tools.gemini_api import google_search

external_signal_agent = LlmAgent(
    name="external_signal",
    model="gemini-2.5-flash",  # or gemini-3-pro-preview
    instruction=prompt.INSTRUCTION,
    tools=[google_search],  # ONLY google_search, cannot add code_executor
    output_key="external_signal_output",
    output_schema=ExternalSignalOutput,
)
```

### Pattern 2: Multi-Agent Coordination (If Mixing Tools)
**What:** Separate agents for search vs other tools, coordinated via root agent
**When to use:** When you need both google_search AND code_executor/other tools
**Example:**
```python
# Source: ADK docs - google.github.io/adk-docs/tools/limitations/
from google.adk.tools import AgentTool

search_agent = LlmAgent(tools=[google_search])
root_agent = SequentialAgent(
    sub_agents=[
        other_agent,  # e.g., numeric_validation with code_executor
        AgentTool(agent=search_agent),  # Wrap search agent
    ]
)
```

### Pattern 3: Processing Grounding Metadata
**What:** Extract citations from groundingMetadata for source tracking
**When to use:** Always - citations prove findings are grounded
**Example:**
```python
# Source: ai.google.dev/gemini-api/docs/google-search
# Response structure:
{
    "candidates": [{
        "content": {...},
        "groundingMetadata": {
            "webSearchQueries": ["Company X lawsuit 2025"],
            "groundingChunks": [
                {"uri": "https://...", "title": "..."}
            ],
            "groundingSupports": [
                {
                    "startIndex": 0,
                    "endIndex": 50,
                    "groundingChunkIndices": [0, 1]
                }
            ]
        }
    }]
}

# Extract sources for findings:
sources = [chunk["uri"] for chunk in grounding_metadata["groundingChunks"]]
```

### Anti-Patterns to Avoid
- **Combining google_search with code_executor in single agent:** Violates one-tool restriction, agent will fail
- **Manual query generation:** Model generates optimal queries autonomously, don't override with fixed query strings
- **Ignoring groundingMetadata:** Citations prove results are grounded; not checking sources = unverifiable findings
- **Custom web scraping:** Violates Google TOS, lacks grounding, unreliable - use google_search instead
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Web search | Custom HTTP requests, BeautifulSoup scraping | google_search tool | TOS compliance, grounding metadata, auto query optimization |
| Query optimization | Manual query string construction | Model-generated queries | Model knows best query patterns for search engines |
| Result ranking | Custom relevance scoring | google_search ranking | Google's ranking algorithm is better than custom heuristics |
| Citation tracking | Manual URL extraction | groundingMetadata structure | Structured citation data with text segment mapping |
| Recency filtering | Date range in query string | Model prompt hints | Model interprets temporal context (e.g., "2025 fiscal year") |

**Key insight:** google_search tool is a complete search solution - query generation, execution, ranking, and citation are handled by Google's infrastructure. Custom web scraping not only violates Terms of Service but produces inferior, ungrounded results without citation metadata.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Mixing google_search with Other Tools
**What goes wrong:** Agent fails to initialize or execute when google_search is combined with code_executor or custom tools
**Why it happens:** ADK enforces "one tool per agent" restriction for google_search
**How to avoid:** Use separate agents (search agent + other agents) coordinated via AgentTool or bypass_multi_tools_limit=True (Python only)
**Warning signs:** Error: "google_search tool cannot be combined with other tools in the same agent"

### Pitfall 2: Treating Search Results as Absolute Truth
**What goes wrong:** 3-27% of AI responses contain errors or outdated information (per false positive research)
**Why it happens:** Search results may include low-quality sources, outdated articles, or contradictory information
**How to avoid:** Process groundingMetadata to extract source URLs, verify critical findings against original sources, flag contradictions for auditor review (not auto-trust)
**Warning signs:** Model reports finding that contradicts financial statement but source URL doesn't support claim

### Pitfall 3: Ignoring Recency Bias
**What goes wrong:** Search surfaces outdated narratives (e.g., 2022 articles about 2025 fiscal year)
**Why it happens:** LLMs strongly favor fresh content but can still surface stale results
**How to avoid:** Include temporal context in prompt (e.g., "for fiscal year 2025", "events in 2025"), verify publication dates in groundingChunks
**Warning signs:** Sources dated 2+ years before reporting period, contradictions with recent events

### Pitfall 4: Over-Trusting Grounded Responses
**What goes wrong:** Assuming grounded = correct, but grounding only means "based on search results" not "verified accurate"
**Why it happens:** Conflating "grounded in sources" with "factually correct"
**How to avoid:** Use grounding for source citations but validate critical claims, flag for auditor review rather than auto-reporting as facts
**Warning signs:** High-impact findings (e.g., "bankruptcy filed") based on single source without verification

### Pitfall 5: Fixed Query Patterns
**What goes wrong:** Hardcoded queries like "Company X lawsuit" miss context-specific signals
**Why it happens:** Trying to control search queries instead of letting model generate them
**How to avoid:** Provide context in prompt (company name, year, specific claims to verify) and let model generate optimal queries
**Warning signs:** Model always uses same query patterns regardless of document context
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources:

### Basic google_search Agent Setup
```python
# Source: google.github.io/adk-docs/tools/gemini-api/google-search/
from google.adk.agents import LlmAgent
from google.adk.tools.gemini_api import google_search

external_signal_agent = LlmAgent(
    name="external_signal",
    model="gemini-2.5-flash",  # Compatible with Gemini 2+
    instruction=prompt.INSTRUCTION,
    tools=[google_search],  # CRITICAL: google_search ONLY
    output_key="external_signal_output",
    output_schema=ExternalSignalOutput,
    temperature=1.0,  # Recommended for grounding (per docs)
)
```

### Processing Grounding Metadata
```python
# Source: ai.google.dev/gemini-api/docs/google-search
def extract_sources(response):
    """Extract source URLs from grounding metadata."""
    grounding_metadata = response.candidates[0].grounding_metadata
    if not grounding_metadata:
        return []

    sources = []
    for chunk in grounding_metadata.grounding_chunks:
        sources.append({
            "url": chunk.uri,
            "title": chunk.title,
        })

    return sources
```

### Prompt Pattern for Company-Specific Search
```python
# Source: Pattern derived from ADK best practices + CONTEXT.md requirements
INSTRUCTION = """You are an external signal agent that searches for risk signals about the company being audited.

## Input

You receive:
1. Financial statement document text (from session state)
2. Company name extracted from document
3. Reporting period year (fiscal year)

## Your Task

Search for external signals that may contradict or contextualize claims in the financial statement.

**Signal types to search:**
1. News articles - Recent company developments, major events, controversies
2. Litigation/legal issues - Lawsuits, regulatory actions, legal proceedings
3. Financial distress signals - Credit downgrades, bankruptcy filings, liquidity concerns

**Search approach:**
- Use company name + year to generate targeted queries
- Search for multiple signal types in parallel (news, litigation, distress)
- Focus on recent timeframe (reporting period + few months prior)
- Use reputable sources only (official filings, major news outlets, regulatory sites)

**Output findings:**
- Signal type (news/litigation/distress)
- Summary of what was found
- Source URL and publication date
- Potential contradiction with financial statement (if any)

## Guidelines

- Focus on reporting period timeframe (e.g., 2025 fiscal year → search 2025 events)
- Use reputable sources only (no social media, no rumors)
- Flag contradictions but don't draw conclusions - auditor will verify
- If no significant signals found, report "No material external signals found"

Let the google_search tool generate optimal queries - you provide context, it handles query construction.
"""
```

### Multi-Agent Workaround (If Mixing Tools)
```python
# Source: google.github.io/adk-docs/tools/limitations/
from google.adk.agents import SequentialAgent
from google.adk.tools import AgentTool

# Separate search agent (google_search only)
search_agent = LlmAgent(
    name="search_sub_agent",
    model="gemini-2.5-flash",
    tools=[google_search],
)

# Root agent coordinates search + other tools
root_agent = SequentialAgent(
    name="orchestrator",
    sub_agents=[
        numeric_validation_agent,  # Uses code_executor
        logic_agent,
        AgentTool(agent=search_agent),  # Wrap search agent as tool
    ]
)
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

What's changed recently:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google_search_retrieval (Gemini 1.x) | google_search (Gemini 2+) | 2024 | New tool for Gemini 2+ models, better grounding metadata |
| Flat pricing ($35/1k prompts) | Usage-based ($14/1k queries) | 2025 (Gemini 3) | More cost-effective for dynamic search workflows |
| Manual tool mixing | bypass_multi_tools_limit | 2025 | Python-only workaround for combining google_search with other tools |

**New tools/patterns to consider:**
- **Interactions API**: Newer ADK API with bypass_multi_tools_limit for tool mixing (Python only, as of 2026-01)
- **Temperature 1.0**: Official recommendation for grounding to optimize search quality
- **groundingSupports**: Fine-grained citation mapping (startIndex/endIndex) for inline citations

**Deprecated/outdated:**
- **google_search_retrieval**: Old tool for Gemini 1.x, replaced by google_search
- **Custom web scraping**: Violates TOS and produces ungrounded results
- **Manual query construction**: Model-generated queries outperform fixed patterns
</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved:

1. **Rate Limits for google_search Tool**
   - What we know: Pricing is $14 per 1,000 queries (Gemini 3), per-query billing suggests rate limits exist
   - What's unclear: Specific rate limits (queries per second/minute), quotas, throttling behavior
   - Recommendation: Start with sequential searches (not massive parallel), monitor for rate limit errors, implement retry logic

2. **Optimal Temperature for Contradiction Detection**
   - What we know: Official docs recommend temperature 1.0 for grounding quality
   - What's unclear: Whether temperature affects contradiction detection sensitivity (higher temp = more creative analysis?)
   - Recommendation: Start with 1.0 (official recommendation), experiment with 0.8-1.0 range if false positives/negatives occur

3. **Search Quality for Legal/Litigation Terms**
   - What we know: google_search uses Google's search index, should handle legal terms well
   - What's unclear: Whether legal databases (PACER, SEC EDGAR) are well-indexed vs just news articles
   - Recommendation: Test with known litigation cases, verify groundingChunks include official sources, may need to explicitly prompt for "official filings" vs news
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [Grounding with Google Search - Gemini API Docs](https://ai.google.dev/gemini-api/docs/google-search) - Tool configuration, groundingMetadata structure, code examples
- [Google Search - Agent Development Kit](https://google.github.io/adk-docs/tools/gemini-api/google-search/) - ADK integration patterns, LlmAgent setup
- [Tool Limitations - ADK Docs](https://google.github.io/adk-docs/tools/limitations/) - One-tool restriction, AgentTool workaround
- [Understanding Google Search Grounding - ADK Docs](https://google.github.io/adk-docs/grounding/google_search_grounding/) - Grounding concepts, best practices

### Secondary (MEDIUM confidence)
- [Grounding with Google Search - Vertex AI Docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search) - Temperature recommendations (1.0), pricing updates
- [New Gemini API updates for Gemini 3](https://developers.googleblog.com/new-gemini-api-updates-for-gemini-3/) - Gemini 3 pricing changes (per query)
- [3 common mistakes to avoid when investing in AI search](https://searchengineland.com/ai-search-mistakes-464084) - Grounding verification, recency bias
- [False Positives in AI Detection: Complete Guide 2026](https://proofademic.ai/blog/false-positives-ai-detection-guide/) - 3-27% error rate in AI responses

### Tertiary (LOW confidence - needs validation)
- WebSearch findings about query patterns - No single authoritative source, best practices inferred from general search optimization guidance
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Gemini google_search tool, ADK LlmAgent
- Ecosystem: Google ADK, multi-agent coordination patterns
- Patterns: Search agent structure, grounding metadata processing, query context
- Pitfalls: Tool mixing, false positives, recency bias, over-trust

**Confidence breakdown:**
- Standard stack: HIGH - Official ADK/Gemini API docs, widely documented
- Architecture: HIGH - From official examples and tool limitation docs
- Pitfalls: MEDIUM - False positive stats from research, one-tool restriction confirmed in docs
- Code examples: HIGH - From official ADK and Gemini API documentation

**Research date:** 2026-01-19
**Valid until:** 2026-02-19 (30 days - Gemini API stable, ADK actively maintained)
</metadata>

---

*Phase: 06-external-signal*
*Research completed: 2026-01-19*
*Ready for planning: yes*
