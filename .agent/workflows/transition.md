---
description: Mark current phase complete and advance to the next phase in the roadmap.
---
<required_reading>

**Read these files NOW:**

1. `.planning/STATE.md`
2. `.planning/PROJECT.md`
3. `.planning/ROADMAP.md`
4. Current phase's plan files (`*-PLAN.md`)
5. Current phase's summary files (`*-SUMMARY.md`)

</required_reading>

<purpose>

Mark current phase complete and advance to next. This is the natural point where progress tracking and PROJECT.md evolution happen.

"Planning next phase" = "current phase is done"

</purpose>

<process>

<step name="load_project_state" priority="first">

Before transition, read project state:

```bash
cat .planning/STATE.md 2>/dev/null
cat .planning/PROJECT.md 2>/dev/null
```

Parse current position to verify we're transitioning the right phase.
Note accumulated context that may need updating after transition.

</step>

<step name="verify_completion">

Check current phase has all plan summaries:

```bash
ls .planning/phases/XX-current/*-PLAN.md 2>/dev/null | sort
ls .planning/phases/XX-current/*-SUMMARY.md 2>/dev/null | sort
```

**Verification logic:**

- Count PLAN files
- Count SUMMARY files
- If counts match: all plans complete
- If counts don't match: incomplete

<config-check>

```bash
cat .planning/config.json 2>/dev/null
```

</config-check>

**If all plans complete:**

<if mode="yolo">

```
⚡ Auto-approved: Transition Phase [X] → Phase [X+1]
Phase [X] complete — all [Y] plans finished.

Proceeding to mark done and advance...
```

Proceed directly to cleanup_handoff step.

</if>

<if mode="interactive" OR="custom with gates.confirm_transition true">

Ask: "Phase [X] complete — all [Y] plans finished. Ready to mark done and move to Phase [X+1]?"

Wait for confirmation before proceeding.

</if>

**If plans incomplete:**

**SAFETY RAIL: always_confirm_destructive applies here.**
Skipping incomplete plans is destructive — ALWAYS prompt regardless of mode.

Present:

```
Phase [X] has incomplete plans:
- {phase}-01-SUMMARY.md ✓ Complete
- {phase}-02-SUMMARY.md ✗ Missing
- {phase}-03-SUMMARY.md ✗ Missing

⚠️ Safety rail: Skipping plans requires confirmation (destructive action)

Options:
1. Continue current phase (execute remaining plans)
2. Mark complete anyway (skip remaining plans)
3. Review what's left
```

Wait for user decision.

</step>

<step name="cleanup_handoff">

Check for lingering handoffs:

```bash
ls .planning/phases/XX-current/.continue-here*.md 2>/dev/null
```

If found, delete them — phase is complete, handoffs are stale.

</step>

<step name="update_roadmap">

Update the roadmap file:

```bash
ROADMAP_FILE=".planning/ROADMAP.md"
```

Update the file:

- Mark current phase: `[x] Complete`
- Add completion date
- Update plan count to final (e.g., "3/3 plans complete")
- Update Progress table
- Keep next phase as `[ ] Not started`

**Example:**

```markdown
## Phases

- [x] Phase 1: Foundation (completed 2025-01-15)
- [ ] Phase 2: Authentication ← Next
- [ ] Phase 3: Core Features

## Progress

| Phase             | Plans Complete | Status      | Completed  |
| ----------------- | -------------- | ----------- | ---------- |
| 1. Foundation     | 3/3            | Complete    | 2025-01-15 |
| 2. Authentication | 0/2            | Not started | -          |
| 3. Core Features  | 0/1            | Not started | -          |
```

</step>

<step name="archive_prompts">

If prompts were generated for the phase, they stay in place.
The `completed/` subfolder pattern from create-meta-prompts handles archival.

</step>

<step name="evolve_project">

Evolve PROJECT.md to reflect learnings from completed phase.

**Read phase summaries:**
```bash
cat .planning/phases/XX-current/*-SUMMARY.md
```

**Assess requirement changes:**
1. **Validated?** Move Active shipped requirements to Validated: `- ✓ [Req] — Phase X`
2. **Invalidated?** Move redundant Active requirements to Out of Scope: `- [Req] — [reason]`
3. **Emerged?** Add new discoveries to Active: `- [ ] [New req]`
4. **Decisions?** Extract from SUMMARY.md and add to Key Decisions table.
5. **Accuracy?** If product changed, update "What This Is" description.

**Update PROJECT.md:** Update "Last updated" footer: `*Last updated: [date] after Phase [X]*`

**Step complete when:**

- [ ] Phase summaries reviewed for learnings
- [ ] Validated requirements moved from Active
- [ ] Invalidated requirements moved to Out of Scope with reason
- [ ] Emerged requirements added to Active
- [ ] New decisions logged with rationale
- [ ] "What This Is" updated if product changed
- [ ] "Last updated" footer reflects this transition

</step>

<step name="update_current_position_after_transition">

Update Current Position section in STATE.md to reflect phase completion and transition.

**Format:**
```markdown
Phase: [next] of [total] ([Next phase name])
Plan: Not started
Status: Ready to plan
Last activity: [today] — Phase [X] complete, transitioned to Phase [X+1]
Progress: [updated progress bar]
```

- Increment phase number, reset plan to "Not started", set status to "Ready to plan".
- Update last activity and progress bar.

</step>

<step name="update_project_reference">

Update Project Reference section in STATE.md.

```markdown
## Project Reference

See: .planning/PROJECT.md (updated [today])

**Core value:** [Current core value from PROJECT.md]
**Current focus:** [Next phase name]
```

Update the date and current focus to reflect the transition.

</step>

<step name="review_accumulated_context">

Review and update Accumulated Context section in STATE.md.

**Decisions:** Note recent decisions (3-5 max). Full log in PROJECT.md.
**Blockers:** Remove addressed blockers; keep relevant ones with "Phase X" prefix. Add new concerns.
**Deferred Issues:** Update count "[N] open issues — see ISSUES.md".

</step>

<step name="update_session_continuity_after_transition">

Update Session Continuity section in STATE.md to reflect transition completion.

**Format:**

```markdown
Last session: [today]
Stopped at: Phase [X] complete, ready to plan Phase [X+1]
Resume file: None
```

**Step complete when:**

- [ ] Last session timestamp updated to current date and time
- [ ] Stopped at describes phase completion and next phase
- [ ] Resume file confirmed as None (transitions don't use resume files)

</step>

<step name="offer_next_phase">

**MANDATORY: Verify milestone status before presenting next steps.**

1. Read ROADMAP.md to identify current phase and milestone phases.
2. Route A (More remain): Offer `/gsd:plan-phase [X+1]`.
3. Route B (Complete): Offer `/gsd:complete-milestone {version}`.

**Route A (More phases):**
<if mode="yolo">
⚡ Auto-continuing: SlashCommand("/gsd:plan-phase [X+1]")
</if>
<if mode="interactive">
Offer `/gsd:plan-phase [X+1]`, `/gsd:discuss-phase`, `/gsd:research-phase`.
</if>

**Route B (Milestone complete):**
<if mode="yolo">
⚡ Auto-continuing: SlashCommand("/gsd:complete-milestone {version}")
</if>
<if mode="interactive">
Offer `/gsd:complete-milestone {version}`.
</if>

</step>

</process>

<implicit_tracking>

Progress tracking is IMPLICIT:

- "Plan phase 2" → Phase 1 must be done (or ask)
- "Plan phase 3" → Phases 1-2 must be done (or ask)
- Transition workflow makes it explicit in ROADMAP.md

No separate "update progress" step. Forward motion IS progress.

</implicit_tracking>

<partial_completion>

If user wants to move on but phase isn't fully complete:

```
Phase [X] has incomplete plans:
- {phase}-02-PLAN.md (not executed)
- {phase}-03-PLAN.md (not executed)

Options:
1. Mark complete anyway (plans weren't needed)
2. Defer work to later phase
3. Stay and finish current phase
```

Respect user judgment — they know if work matters.

**If marking complete with incomplete plans:**

- Update ROADMAP: "2/3 plans complete" (not "3/3")
- Note in transition message which plans were skipped

</partial_completion>

<success_criteria>

Transition is complete when:

- [ ] Current phase plan summaries verified (all exist or user chose to skip)
- [ ] Any stale handoffs deleted
- [ ] ROADMAP.md updated with completion status and plan count
- [ ] PROJECT.md evolved (requirements, decisions, description if needed)
- [ ] STATE.md updated (position, project reference, context, session)
- [ ] Progress table updated
- [ ] User knows next steps

</success_criteria>
