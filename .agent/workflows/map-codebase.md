---
description: Orchestrate parallel Explore agents to analyze the codebase and produce structured docs.
---
<purpose>
Orchestrate parallel Explore agents to analyze codebase and produce structured documents in .planning/codebase/

Each agent has fresh context and focuses on specific aspects. Output is concise and actionable for planning.
</purpose>

<philosophy>
**Parallel Agents:** Fresh context, specialized focus, faster execution.
**Quality:** Prioritize practical examples and code patterns over brevity.
**File Paths:** MANDATORY. Include backticked paths (e.g. `src/file.ts`). No line numbers.
</philosophy>

<process>

<step name="check_existing" priority="first">
Check if `.planning/codebase/` exists: `ls -la .planning/codebase/ 2>/dev/null`

If exists, ask user:
1. **Refresh** (Delete & remap)
2. **Update** (Specific docs)
3. **Skip** (Keep as-is)

- "Refresh": Delete dir, goto create_structure
- "Update": Ask targets, goto spawn_agents (filtered)
- "Skip": Exit
- Else: Goto create_structure
</step>

<step name="create_structure">
Create `.planning/codebase`: `mkdir -p .planning/codebase`

Expected: STACK.md, ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, INTEGRATIONS.md, CONCERNS.md.
Continue to spawn_agents.
</step>

<step name="spawn_agents">
Spawn 4 parallel Explore agents (`subagent_type="Explore"`, `run_in_background=true`).

**Agent 1: Stack & Integrations**
Task: "Analyze tech stack and integrations"
Prompt:
```
Analyze codebase for tech stack and integrations.
MANDATORY: Include actual file paths (e.g., `src/config/db.ts`) for ALL findings.

Find:
1. Languages (extensions, manifests)
2. Runtime (Node, Python, .nvmrc)
3. Pkg managers/lockfiles
4. Frameworks (web, test, build)
5. Critical dependencies
6. External APIs/Services/Auth
7. 3rd-party integrations
8. Config approach (.env, etc)

Output for:
- STACK.md: Languages, Runtime, Frameworks, Deps, Config
- INTEGRATIONS.md: APIs, Services, 3rd-party
```

**Agent 2: Architecture & Structure**
Task: "Analyze architecture/structure"
Prompt:
```
Analyze architecture and directory structure.
MANDATORY: Include actual file paths (e.g., `src/index.ts`) for ALL findings.

Find:
1. Pattern (monolith, microservices, etc)
2. Layers (API, service, data)
3. Data flow & Abstractions
4. Entry points
5. Directory organization & Module boundaries

Output for:
- ARCHITECTURE.md: Patterns, Layers, Flow, Abstractions, Entry
- STRUCTURE.md: Layout, Organization
```

**Agent 3: Conventions & Testing**
Task: "Analyze conventions/testing"
Prompt:
```
Analyze conventions and testing.
MANDATORY: Include actual file paths for ALL findings.

Find:
1. Code style/formatting & Naming
2. Comment style
3. Test framework/structure & types
4. Coverage & Linting tools

Output for:
- CONVENTIONS.md: Style, Naming, Patterns, Docs
- TESTING.md: Framework, Structure, Coverage, Tools
```

**Agent 4: Concerns**
Task: "Identify concerns"
Prompt:
```
Analyze technical debt and concerns.
MANDATORY: Include actual file paths for ALL findings.

Find:
1. TODO/FIXME & Complex code
2. Missing error handling
3. Security/secrets
4. Outdated deps
5. Missing tests
6. Duplication & Perf issues

Output for:
- CONCERNS.md: Debt, Issues, Security, Performance
```

Continue to collect_results.
</step>

<step name="collect_results">
Wait for agents. Use TaskOutput to collect findings.

**Aggregate by document:**
- Agent 1 -> STACK.md, INTEGRATIONS.md
- Agent 2 -> ARCHITECTURE.md, STRUCTURE.md
- Agent 3 -> CONVENTIONS.md, TESTING.md
- Agent 4 -> CONCERNS.md

Missing info? Use "Not detected" or "No significant concerns".
Continue to write_documents.
</step>

<step name="write_documents">
Write 7 docs using templates + findings.

**Process:**
1. Read template `~/.claude/get-shit-done/templates/codebase/{name}.md`
2. Extract "File Template" block.
3. Fill placeholders (Date, Findings).
4. Write to `.planning/codebase/{NAME}.md`.

**Order:**
STACK, INTEGRATIONS, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, CONCERNS.

Continue to verify_output.
</step>

<step name="verify_output">
Check docs: `ls -la .planning/codebase/` count `wc -l`.
Ensure 7 non-empty docs exists.
Continue to commit_codebase_map.
</step>

<step name="commit_codebase_map">
Commit:
```bash
git add .planning/codebase/*.md
git commit -m "docs: map codebase (Stack, Arch, Structure, Conventions, Testing, Integrations, Concerns)"
```
Continue to offer_next.
</step>

<step name="offer_next">
Summary:
```
Codebase mapped in .planning/codebase/:
- STACK.md, ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, INTEGRATIONS.md, CONCERNS.md

---
## ▶ Next Up
**Initialize project** — `/gsd:new-project`
(/clear first)
---
```
End workflow.
</step>

</process>

<success_criteria>
- .planning/codebase/ directory created
- 4 parallel Explore agents spawned with run_in_background=true
- Agent prompts are specific and actionable
- TaskOutput used to collect all agent results
- All 7 codebase documents written using template filling
- Documents follow template structure with actual findings
- Clear completion summary with line counts
- User offered clear next steps in GSD style
</success_criteria>
