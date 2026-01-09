---
description: Create executable PLAN.md (the prompt Claude executes) for a specific phase.
---
<decimal_phase_numbering>
Decimal phases (2.1) allow urgent insertion between valid integers (2, 3) without renumbering.
*   Format: directory `02.1-description/`, plan `02.1-01-PLAN.md`.
*   Validation: Integer X exists/complete, X+1 exists. `2 < 2.1 < 2.2 < 3`.
</decimal_phase_numbering>

<required_reading>
**Read NOW:**
1. ~/.claude/get-shit-done/templates/phase-prompt.md
2. ~/.claude/get-shit-done/references/{plan-format,scope-estimation,checkpoints,tdd}.md
3. .planning/{ROADMAP,PROJECT}.md

**Domain Model:** Parse `ROADMAP.md` "Domain Expertise", read SKILL.md for defined paths, load only relevant references.
</required_reading>

<purpose>
Create executable PLAN.md (the prompt Claude executes).
</purpose>

<planning_principles>
*   **Secure:** Validate all boundaries. Fail closed.
*   **Performant:** Plan for production load/caching.
*   **Observable:** Plan debugging/logging.
</planning_principles>

<process>

<step name="load_project_state" priority="first">
Read `.planning/STATE.md`:
*   Current position/accumulated decisions.
*   Deferred issues/blockers.
If missing, offer reconstruction.
</step>

<step name="load_codebase_context">
Check code map: `ls .planning/codebase/*.md`. Load relevant:
*   Frontend: CONVENTIONS, STRUCTURE
*   Backend: ARCHITECTURE, CONVENTIONS
*   DB: ARCHITECTURE, STACK
*   Tests: TESTING, CONVENTIONS
*   Integration: INTEGRATIONS, STACK
</step>

<step name="identify_phase">
`cat .planning/ROADMAP.md && ls .planning/phases/`.
Parse `^(\d+)(?:\.(\d+))?$` (Int or Dec).
If Decimal: Validate X complete, X+1 exists, X.Y unique.
Read existing PLAN/DISCOVERY if any.
</step>

<step name="mandatory_discovery">
**Discovery is MANDATORY unless context proves existence.**
*   **Level 0 (Skip):** Pure internal/known patterns. (Banned if `Research: Likely`).
*   **Level 1 (Quick 2-5m):** Single library verif. Action: `resolve-library-id`.
*   **Level 2 (Standard 15-30m):** Tradeoffs/Integrations. Action: `discovery-phase.md depth=standard`.
*   **Level 3 (Deep 1h+):** Architecture/Risk. Action: `discovery-phase.md depth=deep`.
</step>

<step name="read_project_history">
**Context from dependency graph:**
1.  **Scan Summaries:** `head -30 .planning/phases/*/*-SUMMARY.md`.
2.  **Build Graph:**
    *   `affects`: Direct dependency.
    *   `subsystem`: Related work.
    *   `requires`: Transitive dependency.
3.  **Select Phases:** Match `affects`, `subsystem`, `requires` chain, or STATE decisions. (Typ. 2-4 phases).
4.  **Extract Meta:** Tech stack, patterns, key files, decisions from frontmatter.
5.  **Read Full:** Open selected SUMMARY.mds for "Ready/Issues/Deviations".
6.  **Scan Issues:** `cat .planning/ISSUES.md`. Filter for phase relevance.
7.  **Track:** Selected refs, tech/patterns, decisions, issues for PLAN frame.
</step>

<step name="gather_phase_context">
Understand goal, existing code, dependencies.
`ls -la src/`, `cat package.json`, `cat .planning/phases/XX-name/${PHASE}-{RESEARCH,CONTEXT}.md`.
*   **RESEARCH.md:** Use `standard_stack` (mandatory), `architecture_patterns`, `code_examples`.
*   **CONTEXT.md:** Honor vision/boundaries.
</step>

<step name="break_into_tasks">
Decompose into tasks. Identify TDD.
**Standard Task:** Type (auto/verify/decision), Name, Files, Action, Verify, Done.
**TDD Candidates:** Business logic, API contracts, Transformers, Algos.
*   **Heuristic:** Can you `expect(fn(in)).toBe(out)` before `fn`? -> TDD Plan.
*   **Why:** TDD loops consume context. Isolate to maintain quality.
**Checkpoints:** `human-verify` (visual), `decision` (choice). Auto external CLIs where possible.
</step>

<step name="estimate_scope">
**Depth controls compression:**
*   Quick: 1-3 plans/phase.
*   Standard: 3-5 plans/phase.
*   Comprehensive: 5-10 plans. Focus on thoroughness not count.

**Must Split:** >3 tasks, >5 files/task, multi-subsystem, complex domain.
**Plan Size:** 2-3 tasks, ~50% context.
**Autonomous:** Group automated tasks (no checkpoints) for subagent execution.
</step>

<step name="confirm_breakdown">
<if mode="yolo">Auto-approve.</if>
<if mode="interactive">
Present breakdown:
```
Phase [X]:
1. [Task] [type]
Autonomous: [y/n]
Confirm?
```
</if>
</step>

<step name="write_phase_prompt">
Use `~/.claude/get-shit-done/templates/phase-prompt.md`.
Write to `.planning/phases/XX-name/{phase}-XX-PLAN.md`.
**Structure:**
*   Frontmatter (Type, Domain)
*   Objective, Execution Context
*   **Context:** `read_project_history` selections + PROJECT/ROADMAP/STATE.
    *   Inject `Tech available`, `Patterns`, `Decisions` from frontmatter.
*   Tasks (XML), Verification, Success Criteria.

Ensure multi-plans link via references and success criteria.
</step>

<step name="git_commit">
```bash
git add .planning/phases/${PHASE}-*/${PHASE}-*-PLAN.md .planning/phases/${PHASE}-*/DISCOVERY.md 2>/dev/null
git commit -m "docs(${PHASE}): create phase plan
Phase ${PHASE}: ${PHASE_NAME}
- [N] plans, [X] tasks"
```
</step>

<step name="offer_next">
Show next step: `/gsd:execute-plan .planning/phases/XX-name/{phase}-01-PLAN.md` (Suggest `/clear`).
</step>
</process>

<task_quality>
*   **Good:** Explicit files, actions, verification. "Add User model to schema".
*   **Bad:** Vague. "Setup auth".
*   **TDD:** If logic warrants, create dedicated TDD plan.
</task_quality>

<success_criteria>
*   [ ] History/STATE absorbed. Discovery complete.
*   [ ] PLAN(s) created (XML structured).
*   [ ] Context injected (Refs, Tech, Patterns, Decisions).
*   [ ] Scope correct (2-3 tasks, <50% context).
*   [ ] Tasks actionable (Files, Action, Verify).
*   [ ] Committed to git.
</success_criteria>
