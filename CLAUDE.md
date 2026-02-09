# Project Rules

## Git Commits

- NEVER add `Co-Authored-By` lines or any AI attribution signatures to commit messages.

## Debugging Agent Runs on Cloud Run

The backend has an agent trace endpoint at `GET /api/v1/jobs/{job_id}/agent-trace` that downloads the ADK debug YAML file for a specific job. These files are written by ADK's `DebugLoggingPlugin` after each agent run completes.

Use this when investigating agent pipeline issues on Cloud Run (you can't exec into containers):
```bash
# Download agent trace for a specific job
curl -o adk_debug.yaml https://<backend-url>/api/v1/jobs/{job_id}/agent-trace
```

The debug YAML contains full agent state at each step — look for output keys like `extracted_tables_raw`, `numeric_validation_output`, etc. to diagnose pipeline issues.
