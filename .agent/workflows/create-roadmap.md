---
description: Define phases of implementation (coherent chunks of value) for a new project.
---
<purpose>
Define phases of implementation (coherent chunks of value). Structure, not detailed tasks.
</purpose>

<required_reading>
**Read these files NOW:**
1. ~/.claude/get-shit-done/templates/roadmap.md
2. ~/.claude/get-shit-done/templates/state.md
3. `.planning/PROJECT.md` (if exists)
</required_reading>

<process>

<step name="check_brief">
```bash
cat .planning/PROJECT.md 2>/dev/null || echo "No brief found"
```
**If no brief:** Ask to create one or proceed. If proceeding, gather:
- What are we building?
- Rough scope?
</step>

<step name="detect_domain">
Scan expertise: `ls ~/.claude/skills/expertise/ 2>/dev/null`

**Inference:** Match brief to domains (e.g., "macOS" → `macos-apps`, "Unity" → `unity-games`, "iOS" → `iphone-apps`, "GLSL" → `isf-shaders`, "Tailwind" → `ui-design`).

**Action:**
1. If domain inferred: Ask to include.
2. If multiple: Ask to select.
3. If none obvious: List available and ask user.

**Store selected paths** for ROADMAP.md.
</step>

<step name="identify_phases">
Derive phases from actual work. Check depth: `cat .planning/config.json 2>/dev/null | grep depth`

<depth_guidance>
**Depth = compression tolerance.**
- **Quick:** 3-5 phases. Aggressively combine work. Critical path only.
- **Standard:** 5-8 phases.
- **Comprehensive:** 8-12 phases. Each major capability separate.

**Rules:**
- Use integer phases (1, 2) for planned work.
- Use decimal phases (2.1) ONLY for urgent insertions (bugs, hotfixes) later.
- Execution order: 1 → 1.1 → 2.
</depth_guidance>

**Deriving phases:**
1. List distinct systems/features.
2. Group into coherent deliverables (one complete thing per phase).
3. If unrelated capabilities: split. If incomplete: merge.
4. Order by dependencies.
5. Common: Foundation → Core → Enhancement → Polish.
</step>

<step name="detect_research_needs">
**Scan phases for research triggers:**

**Likely (Flag Phase):**
- External APIs/Services (Stripe, Twilio, OAuth).
- New tech/integrations (Databases, AI models, libraries not in repo).
- Explicit decisions needed ("choose between X and Y").
- Architectural decisions (Real-time sync, Auth strategy).

**Unlikely:**
- Internal UI/logic "add button", "refactor".
- Standard patterns or existing tech.

**Action:**
For each phase, visually assess:
- `Research: Likely (reason)` + `Topics: ...`
- `Research: Unlikely (reason)`
</step>

<step name="confirm_phases">
Check config. If `yolo` mode, auto-approve.

**Interactive Mode:**
Present breakdown:
"1. [Phase] - [Goal] ... Does this feel right? (yes / adjust)"
</step>

<step name="decision_gate">
If `yolo`, proceed.
If `interactive`, ask: "Ready to create roadmap, or ask more questions?"
</step>

<step name="create_structure">
```bash
mkdir -p .planning/phases
```
</step>

<step name="write_roadmap">
Use template: `~/.claude/get-shit-done/templates/roadmap.md`

**Write to `.planning/ROADMAP.md`**:
- **Domain Expertise**: Selected paths or "None".
- **Phases**: numbered list (1, 2, 3) with one-line descriptions.
- **Dependencies**: sequencing.
- **Research Flags**: Add `Research: Likely/Unlikely` and topics from previous step.
- **Status**: All "not started".

Create directories:
```bash
mkdir -p .planning/phases/01-{phase-name}
# ... for all phases
```
</step>

<step name="initialize_project_state">
Create `.planning/STATE.md` using `~/.claude/get-shit-done/templates/state.md`.

**Content Structure:**
```markdown
# Project State

## Project Reference
See: .planning/PROJECT.md (updated [date])
**Core value:** [From PROJECT.md]
**Current focus:** Phase 1 — [Name]

## Current Position
Phase: 1 of [N] ([Name])
Plan: Not started
Status: Ready to plan
Last activity: [date] — Project initialized
Progress: ░░░░░░░░░░ 0%

## Performance Metrics
**Velocity:**
- Total plans: 0
- Execution time: 0 hours
**By Phase:** (Empty table)
**Recent Trend:** (None)

## Accumulated Context
### Decisions
(None yet)
### Deferred Issues
(None yet)
### Blockers/Concerns
(None yet)

## Session Continuity
Last session: [date/time]
Stopped at: Project initialization complete
Resume file: None
```
</step>

<step name="git_commit_initialization">
Commit brief, roadmap, and state:
```bash
git add .planning/PROJECT.md .planning/ROADMAP.md .planning/STATE.md .planning/phases/ .planning/config.json 2>/dev/null
git commit -m "$(cat <<'EOF'
docs: initialize [project-name] ([N] phases)

[One-liner from PROJECT.md]

Phases:
1. [phase-name]: [goal]
...
EOF
)"
```
</step>

<step name="offer_next">
Display summary (Brief, Roadmap, State created).

**Next Up:**
**Phase 1: [Name]** — [Goal]
`/gsd:plan-phase 1`

*(Suggest `/clear` first)*
**Options:** `/gsd:discuss-phase 1`, `/gsd:research-phase 1`.
</step>

</process>

<phase_naming>
Format: `01-kebab-case-name`.
Examples: `01-foundation`, `02-authentication`.
</phase_naming>

<anti_patterns>
No time estimates, Gantt charts, resource allocation, or arbitrary phase counts.
Phases are work buckets, not management artifacts.
</anti_patterns>

<success_criteria>
- [ ] `.planning/ROADMAP.md` created with clear phases.
- [ ] `.planning/STATE.md` initialized.
- [ ] **Research flags assigned** (Likely/Unlikely + topics).
- [ ] Phase directories created.
- [ ] Dependencies noted.
</success_criteria>
