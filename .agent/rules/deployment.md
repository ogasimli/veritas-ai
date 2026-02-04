---
description: Rules for deploying agents to Cloud Run using ADK
---

# ADK Cloud Run Deployment Rules

When troubleshooting or configuring deployments using `adk deploy cloud_run`:

1.  **Dependency Management**: 
    - The ADK build process for Cloud Run creates an isolated Docker build that **does not** respect `pyproject.toml` dependencies by default.
    - You **MUST** provide a `requirements.txt` file inside the agent's package directory (e.g., `veritas_ai_agent/requirements.txt`).
    - This file must contain all runtime dependencies, *especially* those not included in the standard ADK installation (like `markdown-table-extractor`, `babel`, etc.).

2.  **Synchronization**:
    - Ensure `requirements.txt` is synchronized with `pyproject.toml`.
    - Use `uv pip compile pyproject.toml --output-file <agent_package_dir>/requirements.txt` to automatically generate this file before deployment.

3.  **Authentication**:
    - Ensure `gcloud` is authenticated and looking at the correct project/region.
