### **Implementation Plan: Correct Git Repository Detection**

**Objective:** To replace the current file-based check for a Git repository with a robust, command-based check. This will allow the `sw-build` tool to correctly identify a Git repository even when `MANUALS_DIR` is set to a subdirectory within the repository's work tree.

**Analysis:** The current implementation `os.path.isdir(os.path.join(manuals_dir, '.git'))` fails because it only checks for a `.git` directory at the top level of the specified `manuals_dir` path. It does not traverse up the file system to find the repository root, which is standard behavior for Git commands. The proposed solution is to create a new helper function that uses `git rev-parse` to reliably determine if any given path is part of a Git repository.

---

### **Phase 1: Implement a Robust Git Repository Check**

**Goal:** Create a new, reusable function in `git.py` that accurately determines if a directory is part of a Git work tree.

1.  **File to Modify:** `topdata_package_release_builder/git.py`

2.  **Action:** Add the following function to the end of the file. This function will run a native Git command to perform the check, correctly mimicking the behavior of the Git client.

3.  **Code to Add:**
    ```python
    # In: topdata_package_release_builder/git.py

    import subprocess
    import os
    # (other imports exist)

    # ... (existing functions) ...

    def is_git_repository(repo_path: str, verbose: bool = False, console=None) -> bool:
        """Checks if the specified path is inside a Git repository work tree."""
        if not os.path.isdir(repo_path):
            return False
            
        original_dir = os.getcwd()
        try:
            os.chdir(repo_path)
            if verbose and console:
                console.print(f"[dim]→ Checking if '{os.path.abspath(repo_path)}' is a git repository...[/dim]")
            
            # Use 'git rev-parse' as it's a reliable, low-overhead way to check.
            # It exits with 0 if in a repo, non-zero otherwise.
            result = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                capture_output=True,  # Suppress stdout/stderr from console
                check=False,
                text=True
            )
            
            is_repo = result.returncode == 0 and result.stdout.strip() == "true"
            if verbose and console:
                console.print(f"[dim]→ Is git repository: {'Yes' if is_repo else 'No'}[/dim]")
            
            return is_repo

        except (FileNotFoundError, Exception):
            # Handles cases where git command is not found or other errors
            if verbose and console:
                console.print("[yellow]→ Git command check failed, assuming not a repository.[/yellow]")
            return False
        finally:
            os.chdir(original_dir)
    ```

### **Phase 2: Integrate the New Check into the CLI Workflow**

**Goal:** Replace the old, flawed file system check in `cli.py` with a call to the new `is_git_repository` function.

1.  **File to Modify:** `topdata_package_release_builder/cli.py`

2.  **Action 1: Import the new function.**
    *   Update the `from .git import ...` statement to include `is_git_repository`.

    *   **Key Change:**
        ```python
        # In: topdata_package_release_builder/cli.py

        from .git import (
            get_git_info, check_git_status, stage_changes, commit_and_tag, push_changes,
            pull_changes_in_repo, commit_and_push_changes, is_git_repository
        )
        ```

3.  **Action 2: Replace the check logic.**
    *   Find the `if` condition that checks for the `.git` directory and replace it with the new function call.

    *   **Change this section:**
        ```python
        # --- BEFORE ---
        # ...
        # 2. Check if the directory is a git repo and then commit/push
        if os.path.isdir(os.path.join(manuals_dir, '.git')):
            try:
                status.update("[bold blue]Publishing manual to git repository...")
        # ...
        ```

    *   **To this:**
        ```python
        # --- AFTER ---
        # ...
        # 2. Check if the directory is a git repo and then commit/push
        if is_git_repository(manuals_dir, verbose=verbose, console=console):
            try:
                status.update("[bold blue]Publishing manual to git repository...")
        # ...
        ```

---

### **Phase 3: Verification and Testing**

**Goal:** Confirm that the new logic works as expected and has not introduced any regressions.

1.  **Test Environment Setup:**
    *   Ensure your `.env` file's `MANUALS_DIR` points to a **subdirectory** of a Git repository (e.g., `MANUALS_DIR=/topdata/sw6-plugin-manuals/docs`).

2.  **Test Case 1: The Fix (Happy Path)**
    *   **Action:** Run `sw-build -v` for a plugin with a `manual/` directory.
    *   **Expected Result:**
        *   The verbose output should now show `→ Is git repository: Yes`.
        *   The script should proceed to the "Publishing manual to git repository..." step.
        *   The git `pull`, `commit`, and `push` operations should execute successfully on the parent repository.

3.  **Test Case 2: Non-Git Directory**
    *   **Action:** Temporarily change `MANUALS_DIR` in your `.env` to point to a directory that is **not** part of any Git repository (e.g., `/tmp/not-a-repo`).
    *   **Expected Result:**
        *   The verbose output should show `→ Is git repository: No`.
        *   The script should gracefully skip the Git operations and print the message `→ MANUALS_DIR '...' is not a git repository, skipping auto-commit.`

4.  **Test Case 3: Regression Test (Root Directory)**
    *   **Action:** Temporarily change `MANUALS_DIR` to point to the **root** of your manuals repository (e.g., `/topdata/sw6-plugin-manuals`).
    *   **Expected Result:** The build should succeed, and the Git operations should be performed correctly, confirming that the old working behavior is still supported.

