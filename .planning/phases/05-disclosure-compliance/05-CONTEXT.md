# Phase 5: Disclosure Compliance - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<vision>
## How This Should Work

Smart scanner approach that only validates relevant standards rather than checking 50+ irrelevant standards per document. The agent should:

1. **Scan the document** using keyword/topic detection to identify which IFRS/IAS standards are actually applicable (e.g., if "revenue" appears, check IFRS 15; if "leases" appear, check IFRS 16)

2. **Parallelize validation** by running separate checks for each identified standard, verifying that required disclosures are present

3. **Report gaps clearly** - "IFRS 15 requires disclosure of contract balances, not found in Note X"

The system should be intelligent about what to check, avoiding wasted effort on standards that clearly don't apply to the document.

</vision>

<essential>
## What Must Be Nailed

All three components are equally critical:

- **Accurate standard detection** - The scanner must correctly identify which IFRS standards apply without false positives or misses
- **Complete disclosure checklists** - YAML file must have comprehensive, accurate lists of required disclosures for each standard
- **Clear gap identification** - Findings must precisely indicate what's missing and where it should be

Getting any one wrong undermines the whole system.

</essential>

<boundaries>
## What's Out of Scope

- **Non-IFRS frameworks** - US GAAP and other regional standards deferred to future versions (IFRS only for v1)
- **Industry-specific guidance** - Special rules for banks, insurance, oil & gas - stick to general IFRS requirements
- **Quantitative disclosures** - Focus on whether disclosures *exist*, not validating the numbers within them (numeric validation handles that)
- **Historical standard versions** - Only check current IFRS requirements, not older versions or transition rules

</boundaries>

<specifics>
## Specific Ideas

**Architecture (mirrors numeric_validation pattern):**

Root agent is a SequentialAgent with 2 sub-agents:

1. **Scanner agent** (like Extractor):
   - Analyzes financial statement text
   - Identifies applicable IFRS/IAS topics via keyword/topic detection
   - Outputs: list of applicable standards (e.g., ["IAS 1", "IFRS 15", "IFRS 16"])

2. **FanOutVerifier agent** (like FanOutVerifier):
   - Receives list of applicable standards from Scanner
   - Parallelizes per standard
   - For each standard: uses a tool to load disclosure checklist from YAML file
   - Checks if required disclosures are present in the document
   - Outputs: findings for missing disclosures

**Data structure:**
- Single YAML file containing all standards and their required disclosures
- Structure: standard → list of required disclosures
- Tool integration to load the relevant section per standard

**Initial task:**
- Convert existing Excel file to YAML format
- Excel file location: `~/Downloads/IFRS_e_Check_2024_global_versionv1_5_FINALxlsm`
- This is the first task in the phase - prerequisite for agent implementation

**Standards coverage:**
- All major IFRS standards (15-20 standards)
- Covers comprehensive scenarios, not just the most common ones
- Examples: IAS 1 (Presentation), IAS 7 (Cash Flows), IAS 24 (Related Party), IFRS 7 (Financial Instruments), IFRS 15 (Revenue), IFRS 16 (Leases), and others

**Pattern reuse:**
- Same SequentialAgent → FanOutVerifier architecture as numeric_validation (Phase 3)
- Scanner analogous to Extractor
- FanOutVerifier creates parallel agents per standard, just like it did per FSLI

</specifics>

<notes>
## Additional Context

The disclosure compliance agent is the third sub-agent that will be added to the orchestrator (after numeric_validation and logic_consistency). It runs in parallel with the other validation agents.

Key insight: By scanning first to identify applicable standards, we avoid the computational cost and noise of checking 50+ standards when only 5-8 typically apply to any given document.

The YAML file serves as the knowledge base - keeping it separate from code makes it easy to update disclosure requirements as IFRS standards evolve without touching agent logic.

</notes>

---

*Phase: 05-disclosure-compliance*
*Context gathered: 2026-01-18*
