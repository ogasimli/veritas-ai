# Project Rules

## Git Commits

- NEVER add `Co-Authored-By` lines or any AI attribution signatures to commit messages.

## Debugging Agent Runs on Cloud Run

Agent trace endpoints live under `GET /api/v1/jobs/{job_id}/agent-traces/`:

- **`adk-debug-yaml`** — Downloads the ADK debug YAML (full agent state at each step). Written by `DebugLoggingPlugin` after each run completes.
- **`real-time-trace`** — Returns the `[logging_plugin]` console log for the job. Written continuously during processing so clients can poll for real-time progress. Supports `?offset=<bytes>` for incremental reads; response includes `X-Log-Offset` and `X-Job-Status` headers.

```bash
# Download ADK debug YAML
curl -o adk_debug.yaml https://<backend-url>/api/v1/jobs/{job_id}/agent-traces/adk-debug-yaml

# Follow real-time trace (poll with offset)
curl https://<backend-url>/api/v1/jobs/{job_id}/agent-traces/real-time-trace
curl https://<backend-url>/api/v1/jobs/{job_id}/agent-traces/real-time-trace?offset=4096
```

The debug YAML contains full agent state at each step — look for output keys like `extracted_tables_raw`, `numeric_validation_output`, etc. to diagnose pipeline issues.
