---
description: Pre-planning research on expert implementation patterns and pitfalls for niche/complex domains.
---
<purpose>
Pre-planning research to produce RESEARCH.md. Focuses on expert implementation patterns, standard stacks, and pitfalls for niche/complex domains where LLM training might be stale.
</purpose>

<when_to_use>
- **Use for complex/niche domains:** 3D/WebGPU, Game dev/ECS, Audio/DSP, Shaders, AI/ML integration, Real-time sync/RTC, or fast-moving frameworks.
- **Skip for commodity tasks:** Basic Auth, CRUD, Forms, or standard third-party APIs (Stripe, etc.).
</when_to_use>

<key_insight>
Moving beyond "which library?", this workflow identifies architecture patterns, standard expert stacks, common pitfalls, and current SOTA vs. stale knowledge. It prevents hand-rolling complex solutions.
</key_insight>

<process>

<step name="validate_phase" priority="first">
Validate phase exists in roadmap:
```bash
if [ -f .planning/ROADMAP.md ]; then
  grep -A5 "Phase ${PHASE}:" .planning/ROADMAP.md || (echo "Error: Phase ${PHASE} not found"; exit 1)
fi
```
Extract phase details (Name, Description) and continue.
</step>

<step name="check_existing">
Check for existing RESEARCH.md:
```bash
ls .planning/phases/${PHASE}-*/{RESEARCH.md,${PHASE}-RESEARCH.md} 2>/dev/null
```
If exists, ask user: **Update** (refresh), **View** (show content), or **Skip** (exit).
</step>

<step name="load_context">
Load context to inform research:
1. **Project:** `.planning/PROJECT.md` (first 50 lines)
2. **Phase Context:** `.planning/phases/${PHASE}-*/${PHASE}-CONTEXT.md`
3. **Decisions:** `.planning/STATE.md` (Accumulated Decisions)

Present findings and proceed.
</step>

<step name="identify_domains">
Identify research needs based on phase description:
- **Core Technology:** Framework versions and standard toolchains.
- **Ecosystem:** Essential helper libraries and "blessed" stacks.
- **Patterns:** Expert architecture and project organization.
- **Pitfalls:** Common "gotchas" and performance issues.
- **Don't Hand-Roll:** Existing solutions for complex sub-problems.
- **SOTA:** Recent ecosystem shifts and outdated patterns.
</step>

<step name="execute_research" priority="high">
Research systematically for each domain:

**1. Context7 First (Current/Authoritative):**
- Use `mcp__context7__resolve-library-id` for main tech.
- Use `mcp__context7__get-library-docs` for setup, specific concerns, and integration patterns.

**2. Official Documentation/Ecosystem:**
- Use WebFetch for docs not in Context7.
- Search for "awesome-{tech}" and GitHub trending.

**3. WebSearch for Discovery (Verification Required):**
- Query: `[tech] best practices {current_year}`, `[tech] recommended libraries`, `[tech] project structure`.
- **MANDATORY:** Verify WebSearch findings against official docs or Context7. Flag confidence (High/Med/Low).
</step>

<step name="quality_check">
Verify findings against `~/.claude/get-shit-done/references/research-pitfalls.md`:
- [ ] All items investigated; negative claims verified.
- [ ] Multiple sources cross-referenced; URLs provided.
- [ ] Dates and version numbers checked for freshness.
- [ ] Confidence levels assigned; assumptions distinguished from facts.
</step>

<step name="write_research">
Create `.planning/phases/${PHASE}-${SLUG}/${PHASE}-RESEARCH.md` using template `~/.claude/get-shit-done/templates/research.md`.

**Required Sections:**
1. **Standard Stack:** Libraries, versions, and specialized alternatives.
2. **Architecture Patterns:** Structure recommendations and code snippets.
3. **Don't Hand-Roll:** Explicit list of problems with existing library solutions.
4. **Common Pitfalls:** Specific mistakes and how to avoid them.
5. **Verified Examples:** Code patterns from docs showing the "right way".
</step>

<step name="confirm_creation">
Present Summary:
- **Domain/Stack:** libraries identified.
- **Patterns:** Key architecture choices.
- **Pitfalls:** Top risks.
- **Confidence:** Level and reasoning.

Offer next steps: `/gsd:plan-phase ${PHASE}` or deeper lookup.
</step>

<step name="git_commit">
```bash
git add .planning/phases/${PHASE}-${SLUG}/${PHASE}-RESEARCH.md
git commit -m "docs(${PHASE}): complete phase research"
```
</step>

</process>

<success_criteria>
- Phase validated and context loaded.
- Context7 used for core libraries; WebSearch findings cross-verified.
- RESEARCH.md created with stack, architecture, pitfalls, and "don't hand-roll" lists.
- All versions and patterns verified as current SOTA.
- Research committed to git.
</success_criteria>

<integration_with_planning>
Research informs `/gsd:plan-phase`:
- **Library Choice:** Uses "Standard Stack".
- **Task Design:** Follows "Architecture Patterns" and "Code Examples".
- **Risk Mitigation:** Task verification informed by "Common Pitfalls".
- **Efficiency:** Prevents custom builds where "Don't Hand-Roll" applies.
</integration_with_planning>
