---
description: Run lint and tests, and automatically fix any issues until they pass.
---

1.  **Initial Check**: Run `make lint && make test`.
    *   If successful, exit with: "All checks passed!"
    *   If failed, proceed to the fix loop.

2.  **Fix Loop**:
    *   **Analyze**: Read the failure output (lint errors or test tracebacks).
    *   **Fix**: Edit the code to resolve the specific errors identified.
    *   **Retry**: Run `make lint && make test` again.
    *   **Limit**: Repeat this cycle up to **5 times**.

3.  **Final Status**:
    *   **Pass**: Inform the user "Fixed all issues. Checks passing."
    *   **Fail**: Inform the user "Could not fix all issues after 5 attempts." and provide a summary of remaining errors.
