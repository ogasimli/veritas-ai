---
description: Execute a phase plan (PLAN.md) and create the outcome summary (SUMMARY.md).
---
<purpose>
Execute a phase prompt (PLAN.md) and create the outcome summary (SUMMARY.md).
</purpose>

<required_reading>
Read STATE.md before any operation to load project context.
</required_reading>

<process>

<step name="init">
1. **Load State**: Read `.planning/STATE.md`. If missing, error "Project not initialized".
   - Parse: Current position, Accumulated decisions, Deferred issues.
2. **Identify Plan**:
   - Find "In progress" phase in `ROADMAP.md`.
   - Find first `*-PLAN.md` without matching `*-SUMMARY.md` in that phase.
   - Resolve decimal/integer phase number ambiguity if needed.
3. **Record Start**: Store `PLAN_START_TIME` and `PLAN_START_EPOCH` for metrics.
</step>

<step name="segmentation_strategy">
**Determine Execution Mode:**
1. Check for checkpoints: `grep "type=\"checkpoint" {PLAN}`
2. **No Checkpoints (Pattern A)**:
   - Spawn **Subagent** (type="general-purpose").
   - Instruction: "Execute entire plan {path}. Follow deviation rules. Create SUMMARY, commit all tasks."
3. **With Checkpoints (Pattern B/C)**:
   - Parse tasks into segments separated by checkpoints.
   - **Segment Routing**:
     - Preceded by Start OR `checkpoint:human-verify` → **Subagent**.
     - Preceded by `checkpoint:decision` OR `checkpoint:human-action` → **Main Context**.
   - **Execution Loop**:
     - Execute Segment 1 (Subagent/Main).
     - Handle Checkpoint 1 (Main wait for user).
     - Execute Segment 2...
   - **Finalization**: Aggregate results (files, deviations), create SUMMARY in Main, single final metadata commit.
</step>

<step name="execution_rules">
**Applies to both Main Context and Subagent verification.**

**1. Authentication Gates**:
- If CLI/API returns auth error (401/403/"login required"):
- **STOP**. Present `checkpoint:human-action`. "Run [login command]".
- Wait for user. Verify auth. **Resume**. (Do NOT log as failure).

**2. Deviation Handling**:
| Condition | Rule | Action |
|-----------|------|--------|
| Bug/Conflict | Rule 1 | Fix auto. Log in Summary. |
| Missing Critical | Rule 2 | Add auto. Log in Summary. |
| Blocker | Rule 3 | Fix auto. Log in Summary. |
| Architectural Change | Rule 4 | **STOP**. Ask User. |
| Non-critical Enhancement | Rule 5 | Log to `ISSUES.md`. Continue. |

**3. Task Commit Protocol**:
- After EACH task (verified):
- `git add <task-files>` (Atomic!)
- `git commit -m "{type}({phase}-{plan}): {description}"`
- key types: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`.

**4. Checkpoint Protocol**:
- `human-verify`: Show built items, verification steps. Wait for "approved".
- `decision`: Show options/pros/cons. Wait for selection.
- `human-action`: Request manual step. Wait for confirmation.
</step>

<step name="finalize_execution">
1. **Metrics**: Calculate duration from `PLAN_START_EPOCH`.
2. **Create Summary**: Write `{phase}-{plan}-SUMMARY.md`.
   - Frontmatter: phase, plan, tags, metrics.
   - Sections: Accomplishments, Decisions, Deviations (from execution rules), Issues, Next steps.
3. **Update State**:
   - Update `Current Position` (Phase X of Y, Plan A of B).
   - Append new `Decisions` and `Deferred Issues`.
   - Update `Session Continuity` (Last session, Resume file).
4. **Update Roadmap**: Mark plans/phase as complete in `.planning/ROADMAP.md`.
5. **Metadata Commit**:
   - `git add {SUMMARY} STATE.md ROADMAP.md`
   - `git commit -m "docs({phase}-{plan}): complete [name] plan ..."`
6. **Codebase Map**: If `.planning/codebase/` exists and structure changed, update maps.
</step>

<step name="next_transition">
**Determine Next Step:**
1. Check counts in phase: `Plans` vs `Summaries`.
   - `Summaries < Plans`: **Next Plan**.
2. If `Summaries == Plans`: Phase Complete.
   - Check `ROADMAP.md` for proper Milestone progress.
   - If `Current Phase < Max Milestone Phase`: **Next Phase**.
   - If `Current Phase == Max Milestone Phase`: **Milestone Complete**.

**Output Message**:
- **Route A (Next Plan)**: "Plan complete. Next: `{phase}-{next}-PLAN.md` (`/gsd:execute-plan`)."
- **Route B (Next Phase)**: "Phase {X} complete. Next: Phase {Y} (`/gsd:plan-phase`)."
- **Route C (Milestone Done)**: "Milestone Complete! (`/gsd:complete-milestone`)."
</step>

</process>

<success_criteria>
- All plan tasks executed and committed.
- SUMMARY.md created.
- STATE.md and ROADMAP.md updated.
- Git history clean (atomic task commits + 1 metadata commit).
</success_criteria>
