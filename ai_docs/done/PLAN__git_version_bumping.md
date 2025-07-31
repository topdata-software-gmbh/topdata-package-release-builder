# Plan: Integrate Git Version Bumping into sw-build

**1. Goal:**

*   Add a check for uncommitted Git changes at the start of the `sw-build` script.
*   Prompt the user to optionally stage these changes.
*   If a version bump occurs, automatically commit `composer.json`, create a Git tag with the new version, and push the changes (commit and tag) to the remote repository.

**2. Proposed Changes:**

*   **`topdata_package_release_builder/git.py`:**
    *   Create a new function `check_git_status()`:
        *   Uses `subprocess.check_output(['git', 'status', '--porcelain'])`.
        *   Returns `True` if there's output (unstaged/uncommitted changes), `False` otherwise.
    *   Create a new function `stage_changes()`:
        *   Uses `subprocess.check_output(['git', 'add', '.'])` to stage all changes.
    *   Create a new function `commit_and_tag(file_path: str, version: str, message_template: str)`:
        *   Runs `git add <file_path>` (specifically for `composer.json`).
        *   Runs `git commit -m "<formatted message>"`.
        *   Runs `git tag <version>`.
    *   Create a new function `push_changes(branch: str, tag: str)`:
        *   Runs `git push origin <branch>`.
        *   Runs `git push origin <tag>`.
    *   Ensure proper error handling (e.g., using `try...except` around `subprocess` calls or letting exceptions propagate).

*   **`topdata_package_release_builder/cli.py`:**
    *   **Import new functions:** Add imports for `check_git_status`, `stage_changes`, `commit_and_tag`, `push_changes` from `.git`.
    *   **Check Status Early:** After `load_env` (around line 55), call `git.check_git_status()`.
    *   **Prompt for Staging:** If `check_git_status()` returns `True`:
        *   Use `InquirerPy.confirm` to ask the user: `"[?] Found unstaged changes! Would you like to stage these changes?"`
        *   If confirmed, call `git.stage_changes()`.
    *   **Auto Commit/Tag/Push:** Inside the `if bump_type != VersionBump.NONE:` block (after line 95 `update_composer_version`):
        *   Define the commit message: `commit_message = f"bump to version {new_version}"` (using `new_version` from line 94).
        *   Call `git.commit_and_tag('composer.json', new_version, commit_message)`.
        *   Call `git.push_changes(branch, new_version)` (using `branch` from line 70 and `new_version` from line 94).

**3. Workflow Visualization:**

```mermaid
graph TD
    A[Start sw-build] --> B(Load .env);
    B --> C{Check Git Status};
    C -- Changes Found --> D{Ask to Stage?};
    C -- No Changes --> E[Get Git Info (branch, commit)];
    D -- Yes --> F[Stage Changes (git add .)];
    D -- No --> E;
    F --> E;
    E --> G[Get Plugin Info (name, version)];
    G --> H{Select Version Bump};
    H -- Bump Selected --> I[Update composer.json];
    H -- None Selected --> J[Proceed with Build (Copy Files etc.)];
    I --> K[Commit composer.json];
    K --> L[Tag Commit w/ Version];
    L --> M[Push Commit & Tag];
    M --> J;
    J --> N[... Rest of Build Process ...];
    N --> Z[End];

    subgraph "New Git Steps"
        C; D; F; K; L; M;
    end
```

**4. Considerations:**

*   **Error Handling:** The plan relies on `subprocess` raising errors for failed Git commands. These will be caught by the main `try...except` block in `cli.py`, aborting the script. More specific error handling could be added later if needed (e.g., distinguishing between a failed push due to network issues vs. conflicts).
*   **Remote Name:** The `push_changes` function assumes the remote is named `origin`. This is standard but could be made configurable if necessary.
*   **Dependencies:** Assumes `git` is installed and available in the system's PATH.