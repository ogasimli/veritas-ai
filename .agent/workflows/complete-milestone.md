---
description: Mark a shipped version (v1.0, v1.1, etc.) as complete and archive details.
---
<purpose>
Mark a shipped version (v1.0, v1.1, etc.) as complete. Creates record in MILESTONES.md, reviews PROJECT.md, reorganizes ROADMAP.md, archives details, and tags git.
</purpose>

<required_reading>
**Read NOW:**
1. templates/milestone.md
2. templates/milestone-archive.md
3. .planning/ROADMAP.md
4. .planning/PROJECT.md
</required_reading>

<archival_behavior>
When completing a milestone:
1. Extract details to `.planning/milestones/v[X.Y]-ROADMAP.md` (using `templates/milestone-archive.md`)
2. Update ROADMAP.md (replace milestone details with 1-line summary)
3. Link to archive
4. Evolve PROJECT.md
5. Tag release

**Format:** One-line summaries in ROADMAP.md keep it clean. Full history in archive files.
</archival_behavior>

<process>

<step name="verify_readiness">
Check completeness:
```bash
cat .planning/ROADMAP.md
ls .planning/phases/*/SUMMARY.md 2>/dev/null | wc -l
```
Verify phases, plans, and validation status.

<config-check>
```bash
cat .planning/config.json 2>/dev/null
```
</config-check>

<if mode="yolo">
Auto-approve if config allows. Proceed into `gather_stats`.
</if>

<if mode="interactive" OR="custom with gates.confirm_milestone_scope true">
Ask user to confirm scope ("yes", "wait", "adjust scope").
</if>
</step>

<step name="gather_stats">
Calculate stats (phases, plans, files, LOC, timeline):
```bash
# Git range
git log --oneline --grep="feat(" | head -20
# Modified files
git diff --stat FIRST_COMMIT..LAST_COMMIT | tail -1
# LOC
find . -name "*.swift" -o -name "*.ts" -o -name "*.py" | xargs wc -l 2>/dev/null
# Dates
git log --format="%ai" FIRST_COMMIT | tail -1
git log --format="%ai" LAST_COMMIT | head -1
```
Present summary: Phases, Plans, Files, LOC, Timeline, Git range.
</step>

<step name="extract_accomplishments">
Read phase summaries (`.planning/phases/*/*-SUMMARY.md`) and extract 4-6 key accomplishments.
</step>

<step name="create_milestone_entry">
Create/Prepend to `.planning/MILESTONES.md` using `templates/milestone.md`.
Fill details: Version, Name, Date, Accomplishments, Stats, Git range.
Ask user for "Delivered" summary and "What's next".
</step>

<step name="evolve_project_full_review">
Perform full `PROJECT.md` review.

1. **Read phase summaries:** `cat .planning/phases/*-*/*-SUMMARY.md`
2. **"What This Is":** Update if product changed.
3. **Core Value:** Verify or update.
4. **Requirements Audit:**
   - Move shipped Active items to Validated (`- ✓ [Req] — v[X.Y]`).
   - Add new Active items.
   - Audit Out of Scope.
5. **Context:** Update LOC, tech stack, feedback.
6. **Key Decisions:** Add from phase summaries with outcomes.
7. **Constraints:** Update if changed.
8. **Footer:** Update "Last updated".

Ensure `PROJECT.md` reflects the post-milestone state.
</step>

<step name="reorganize_roadmap">
Update `.planning/ROADMAP.md`:
1. Group completed phases under "## Milestones".
2. Use `<details>` for completed milestone phases.
3. Format: `- ✅ **v[Version] [Name]** — Phases [X]-[Y] (shipped [Date])`
4. Remove full details of completed phases from main view.
</step>

<step name="archive_milestone">
1. Target: `.planning/milestones/v[X.Y]-ROADMAP.md`
2. Template: `templates/milestone-archive.md`
3. Extract details from `ROADMAP.md` (phases, plans) and `PROJECT.md` (decisions, validated reqs).
4. Fill template placeholders.
5. Write archive file.
6. Update `ROADMAP.md` with link to archive.
7. Verify file existence.
</step>

<step name="update_state">
Update `.planning/STATE.md`:
* **Project Reference:** Link to updated `PROJECT.md`, Core Value, Current Focus.
* **Position:** "Ready to plan" next milestone.
* **Context:** Summary of decisions/blockers.
</step>

<step name="git_tag">
Create annotated tag `v[X.Y]`:
```bash
git tag -a v[X.Y] -m "v[X.Y] [Name] - [Delivered Summary]"
```
Ask to push: `git push origin v[X.Y]`
</step>

<step name="git_commit_milestone">
Stage and commit:
```bash
git add .planning/MILESTONES.md .planning/PROJECT.md .planning/ROADMAP.md .planning/STATE.md .planning/milestones/v[X.Y]-ROADMAP.md
git commit -m "chore: complete v[X.Y] milestone"
```
</step>

<step name="offer_next">
Summary of completion.
Suggest next steps: `/gsd:discuss-milestone` or `/gsd:new-milestone`.
</step>

</process>

<milestone_naming>
* **Version:** v1.0 (MVP), v1.1 (Minor), v2.0 (Major).
* **Name:** Short (1-2 words), e.g., "MVP", "Security", "Redesign".
</milestone_naming>

<what_qualifies>
**Create for:** Initial release, Public releases, Major feature sets.
**Avoid for:** Granular phase completion, WiP.
</what_qualifies>
