---
trigger: always_on
description: Rules for Git and Commit Operations
---

- **Commit Messages**: NEVER use Markdown formatting in commit messages.
- **No Navigation Links**: NEVER include IDE navigation links, relative paths starting with `./`, or absolute paths in commit messages.
- **Reference Style**: Refer to files by their base name only (e.g., schema.py instead of backend/agents/schema.py) and write them as plain text.
- **Zero Metadata**: Do not include any cci:7:// or similar metadata in any user-visible commit draft.