---
description: safely commit staged changes with auto-fixing of pre-commit hooks
---

1.  **Analyze Staged Changes**: Run `git diff --cached` to see what is staged for commit.
    *   If nothing is staged, stop and warn the user.
2.  **Draft Message**: based on the staged diff, write a commit message that follows the conventional commit format:
    ```
    <type>: <summary>

    <detailed explanation>
    ```
    *   **Rule**: Do NOT include IDE navigation links (e.g., `cci:7://...`) or absolute paths in the message.
    *   **Rule**: Filenames are allowed and encouraged for clarity.
    *   **Rule**: Relative paths is not encouraged, so use it only if absolutely necessary
3.  **User Confirmation**: Show the drafted message to the user and ask: "I propose this commit message. Shall I proceed? (yes/no/edit)"
    *   **STOP**: Wait for user input.
4.  **Protect Unstaged Changes**:
    *   Check `git diff --name-only` (unstaged changes).
    *   If there are unstaged changes:
        *   Run `git stash push -k -u -m "SMOOTH_COMMIT_PROTECTION"`. (`-k` keeps the staged changes indices intact).
        *   Set `STASHED_UNSTAGED = true`.
    *   If no unstaged changes:
        *   Set `STASHED_UNSTAGED = false`.
5.  **Commit & Fix Loop**:
    *   Run `git commit -m "<FINAL_MESSAGE>"`.
    *   **If successful**: Go to step 6.
    *   **If failed** (pre-commit hooks/linting):
        *   Analyze errors in the output.
        *   **Fix** the code files (the ones that are staged) to resolve lint/test errors.
        *   Run `git add <fixed_files>` to update the staging area.
        *   Limit: Retry this loop newly up to **5 times**.
        *   If it still fails after 5 attempts, abort (see Step 7).
6.  **Cleanup (Success)**:
    *   If `STASHED_UNSTAGED` is true:
        *   Run `git stash pop`.
    *   Inform user: "Successfully committed changes."
7.  **Cleanup (Failure/Abort)**:
    *   If `STASHED_UNSTAGED` is true:
        *   Run `git stash pop`. (This might cause conflicts if we tried to fix files that had unstaged changes too, but usually safe).
    *   Inform user: "Failed to commit. Restored original state."