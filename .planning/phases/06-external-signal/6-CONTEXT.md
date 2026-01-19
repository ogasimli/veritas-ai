# Phase 6: External Signal - Context

**Gathered:** 2026-01-19
**Status:** Ready for planning

<vision>
## How This Should Work

Build an agent that searches for external risk signals (news, litigation, financial distress) about the company being audited and flags contradictions with claims made in the financial statements.

**Execution model:** On-demand search triggered when processing a financial statement document - not a periodic monitoring system. Agent receives document, extracts company name and reporting year, performs targeted searches, analyzes results against financial statement claims.

**Signal types to search:**
1. **News articles** - Recent company developments, major events, controversies
2. **Litigation/legal issues** - Lawsuits, regulatory actions, legal proceedings
3. **Financial distress signals** - Credit downgrades, bankruptcy filings, liquidity concerns

**Processing approach:** Flag contradictions between external signals and financial statement claims. For example:
- Financial statement claims "no material litigation" but search finds major ongoing lawsuit
- Financial statement shows revenue growth but news reports plant closures and layoffs
- Financial statement claims stable operations but news reports regulatory investigations

</vision>

<essential>
## What Must Be Nailed

- **Complete risk picture** - Search must be comprehensive enough to surface material external signals that could contradict or contextualize financial statement claims. Auditors need confidence that they're not missing publicly available red flags.

</essential>

<boundaries>
## What's Out of Scope

- **No social media monitoring** - Focus on reputable news sources and official legal/regulatory filings, not Twitter/Reddit sentiment or rumors

- **No competitor analysis** - Search and analyze only the target company being audited, not competitors or market comparisons

- **No historical deep dives** - Focus on recent timeframe relevant to the reporting period (e.g., fiscal year + few months prior), not decades of company history

**In summary:** Recent, reputable, target-company-only signals relevant to the reporting period.

</boundaries>

<specifics>
## Specific Ideas

- **Extract company name AND year** from the financial statement document being processed (e.g., "Acme Corp" + "2025 fiscal year")

- **Use multiple query patterns** for comprehensive coverage:
  - "{Company Name} news {Year}"
  - "{Company Name} lawsuit litigation {Year}"
  - "{Company Name} SEC filing {Year}"
  - "{Company Name} bankruptcy restructuring {Year}"
  - "{Company Name} regulatory investigation {Year}"

- **Use Gemini's google_search tool** (research needed on exact API/integration)

- **Output structure:** List of findings with:
  - Signal type (news/litigation/distress)
  - Source (URL, publication, date)
  - Summary (key facts from the signal)
  - Potential contradiction (what financial statement claim this might contradict)

</specifics>

<notes>
## Additional Context

This is the final validation agent before the frontend dashboard (Phase 7).

**Current validation agents:**
- numeric_validation: Math errors in tables (code execution)
- logic_consistency: Semantic contradictions within document
- disclosure_compliance: IFRS checklist verification
- external_signal (Phase 6): Public information contradicting financial statement claims

**Research needed:** Gemini google_search tool API - how to invoke, query format, result structure, rate limits, grounding patterns.

**Timeframe consideration:** Financial statements typically cover prior fiscal year (e.g., report dated March 2026 for FY2025). Search should focus on events during the reporting period + few months prior (e.g., calendar year 2025 + Q4 2024 for context).

</notes>

---

*Phase: 06-external-signal*
*Context gathered: 2026-01-19*
