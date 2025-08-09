# Refactoring Plan: Extracting Logic from `cli.py`

This plan is designed to be executed incrementally, ensuring that the application remains in a functional state after each phase.

### Refactoring Goal

To reduce the size and complexity of `topdata_package_release_builder/cli.py` by moving two distinct, self-contained processes (the versioning workflow and the manuals publishing workflow) into a new, dedicated `workflow.py` module.

---

### Phase 1: Preparation and Scaffolding

**Objective:** Create the new module and its necessary structure without altering any existing logic. This phase involves no functional changes and is completely safe.

*   **Step 1.1: Create the New File**
    *   In the `topdata_package_release_builder/` directory, create a new file named `workflow.py`.

*   **Step 1.2: Add Initial Content to `workflow.py`**
    *   Open `workflow.py` and add a docstring and the necessary imports that we anticipate needing for the upcoming phases.

    ```python
    # topdata_package_release_builder/workflow.py
    """
    Houses self-contained business logic workflows extracted from the main CLI.

    This module helps to keep the cli.py file clean and focused on command-line
    argument parsing and high-level orchestration.
    """
    from InquirerPy import inquirer

    from .config import get_manuals_dir
    from .git import (commit_and_tag, push_changes, is_git_repository,
                      pull_changes_in_repo, commit_and_push_changes)
    from .manual import copy_manuals
    from .version import VersionBump, bump_version, update_composer_version
    ```

*   **Verification for Phase 1:**
    *   The project is still fully functional. Run `sw-build --help` to confirm that the application starts correctly and no errors are introduced.

---

### Phase 2: Extract the Versioning Workflow

**Objective:** Move the entire logic for version selection, bumping, and Git operations into a function within `workflow.py`.

*   **Step 2.1: Define the Function in `workflow.py`**
    *   In `workflow.py`, define the new function `handle_versioning_workflow`.

    ```python
    def handle_versioning_workflow(
        original_version: str,
        current_version: str,
        branch: str,
        source_dir: str,
        version_increment_cli: str | None,
        console,
        verbose: bool
    ) -> str:
        """
        Handles the user interaction for version bumping, updates files, and commits to git.
        Returns the selected version string (without 'v' prefix).
        """
        # The code from cli.py will be pasted here in the next step.
        pass # Placeholder for now
    ```

*   **Step 2.2: Move the Code from `cli.py` to `workflow.py`**
    *   **Cut** the following block of code from `cli.py`. It starts after the `status.stop()` call and ends after the `push_changes(...)` call.

    ```python
    # --- This is the block to CUT from cli.py ---
    major_version = get_major_version(original_version)
    
    version_choice = None
    if version_increment:
        # ... (all the if/elif mapping version_increment to version_choice)
    else:
        # ... (the entire "else" block with InquirerPy prompt)

    # Update version if needed
    bump_type = VersionBump(version_choice)
    if bump_type != VersionBump.NONE:
        new_version = bump_version(original_version, bump_type)
        update_composer_version(new_version, verbose=verbose, console=console)
        version = new_version.lstrip('v')
        if verbose:
            console.print(f"[dim]→ Version updated to: {new_version}[/]")

        # Auto commit, tag, and push
        commit_message = f"bump to version {new_version}"
        commit_and_tag('composer.json', new_version, commit_message, source_dir=source_dir, verbose=verbose, console=console)
        push_changes(branch, new_version, source_dir=source_dir, verbose=verbose, console=console)
    ```
    *   **Paste** this code into the `handle_versioning_workflow` function in `workflow.py`, replacing the `pass` statement.

*   **Step 2.3: Adapt the Pasted Code**
    *   In `workflow.py`, change the variable `version_increment` to `version_increment_cli` to match the function's parameter name.
    *   Ensure the function returns the correct version at the end.

    ```python
    # In workflow.py, inside handle_versioning_workflow

    # ... (the pasted code) ...

    bump_type = VersionBump(version_choice)
    if bump_type == VersionBump.NONE:
        return current_version # Return the unchanged version

    new_version_str = bump_version(original_version, bump_type)
    update_composer_version(new_version_str, verbose=verbose, console=console)
    
    # ... (git commit and push logic) ...

    return new_version_str.lstrip('v') # Return the new version string
    ```

*   **Step 2.4: Update `cli.py` to Use the New Function**
    *   Add the new import at the top of `cli.py`:
        `from .workflow import handle_versioning_workflow`
    *   In `cli.py`, where you cut the code from, add a call to the new function:

    ```python
    # In cli.py, inside the build_plugin function

    status.stop()  # Stop status for interactive prompt
    version = handle_versioning_workflow(
        original_version=original_version,
        current_version=version,
        branch=branch,
        source_dir=source_dir,
        version_increment_cli=version_increment,
        console=console,
        verbose=verbose
    )
    status.start()  # Restart status for subsequent steps
    ```

*   **Verification for Phase 2:**
    *   Run `sw-build` with different versioning options:
        1.  `sw-build` (interactive prompt).
        2.  `sw-build --version-increment patch`.
        3.  `sw-build --version-increment none`.
    *   Confirm that `composer.json` is updated correctly and that new tags are pushed to your Git repository. The behavior should be identical to before the refactoring.

---

### Phase 3: Extract the Manuals Publishing Workflow

**Objective:** Move the logic for copying and publishing documentation into a second function within `workflow.py`.

*   **Step 3.1: Define the Function in `workflow.py`**
    *   Below the first function in `workflow.py`, define `publish_manuals_workflow`.

    ```python
    def publish_manuals_workflow(
        plugin_name: str,
        version: str,
        source_dir: str,
        status,  # The rich status object
        console,
        verbose: bool
    ):
        """Handles copying manuals and publishing them to a git repository if configured."""
        pass # Placeholder for now
    ```

*   **Step 3.2: Move the Code from `cli.py` to `workflow.py`**
    *   **Cut** the following block from `cli.py`. It starts with `manuals_dir = get_manuals_dir(...)`.

    ```python
    # --- This is the block to CUT from cli.py ---
    manuals_dir = get_manuals_dir(verbose=verbose, console=console)
    if manuals_dir:
        # 1. Copy the files first
        status.update("[bold blue]Copying manuals...")
        copy_manuals(plugin_name, version, manuals_dir, source_dir, verbose=verbose, console=console)
        
        # 2. Check if the directory is a git repo and then commit/push
        # ... (the entire rest of the if/elif block) ...
    ```
    *   **Paste** this code into the `publish_manuals_workflow` function in `workflow.py`.

*   **Step 3.3: Update `cli.py` to Use the New Function**
    *   Add `publish_manuals_workflow` to the import statement at the top of `cli.py`.
    *   Where you cut the code from (inside the `with tempfile.TemporaryDirectory() as temp_dir:` block), add the new function call:

    ```python
    # In cli.py, inside the with temp_dir block
    
    # ... (code to create the zip archive) ...

    # --- Publish Documentation ---
    publish_manuals_workflow(
        plugin_name=plugin_name,
        version=version,
        source_dir=source_dir,
        status=status,
        console=console,
        verbose=verbose
    )
    
    # ... (rest of the with block) ...
    ```

*   **Verification for Phase 3:**
    *   Run `sw-build` on a project with a `/manual` directory and `MANUALS_DIR` configured in your `.env` file.
    *   Confirm that the manual files are copied and that the Git operations (pull, add, commit, push) are performed on the manuals repository.
    *   Run the command without `MANUALS_DIR` configured and ensure it skips this step gracefully.

---

### Phase 4: Final Cleanup

**Objective:** Remove now-unused imports from `cli.py` to finalize the refactoring.

*   **Step 4.1: Review and Clean Imports in `cli.py`**
    *   The following imports are likely no longer needed directly in `cli.py` because their usage has moved to `workflow.py`. Review and remove them.
        *   `from InquirerPy import inquirer`
        *   `from .git import stage_changes, commit_and_tag, push_changes, pull_changes_in_repo, commit_and_push_changes, is_git_repository` (some of these might still be needed for the unstaged changes check).
        *   `from .version import VersionBump, bump_version, update_composer_version, get_major_version`
        *   `from .manual import copy_manuals`
    *   Be careful to leave imports that are still used (e.g., `check_git_status` and `stage_changes`).

*   **Verification for Phase 4:**
    *   After removing unused imports, run a final, full test of the `sw-build` command with several options (`--notify-slack`, `--no-sync`, variant creation) to ensure all functionality remains intact and no `ImportError` exceptions occur.



