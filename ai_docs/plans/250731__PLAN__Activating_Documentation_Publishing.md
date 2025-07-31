# Implementation Plan: Activating Documentation Publishing in the Release Builder

**Objective:** To modify the `topdata-package-release-builder` to correctly utilize the `MANUALS_DIR` environment variable, enabling the automatic publishing of a plugin's documentation to a central repository during the release process.

**Current State Analysis:** The builder's modules are correctly designed (`config.py` can read the variable, `manual.py` contains the copy logic), but the main `cli.py` script fails to orchestrate these components. The core logic to invoke the manual copying function is missing.

---

## Phase 1: Core Logic Implementation and Functional Fix

**Goal:** To implement the missing orchestration logic in `cli.py` so that the documentation is copied when the build is run.

### Key Tasks:

1.  **Modify `topdata_package_release_builder/cli.py`:**
    *   **Location:** Inside the `build_plugin` function, immediately after the line `create_archive(...)`. This ensures that documentation is only published if the primary artifact (the ZIP file) is created successfully.
    *   **Action:** Insert the following logic block:
        ```python
        # Get MANUALS_DIR from environment configuration
        manuals_dir = get_manuals_dir(verbose=verbose, console=console)

        # Check if the directory is configured
        if manuals_dir:
            # Update the console status for the user
            status.update("[bold blue]Publishing documentation...")
            
            # Call the existing copy function with the necessary parameters
            copy_manuals(plugin_name, version, manuals_dir, verbose=verbose, console=console)
        
        # If not configured and in verbose mode, inform the user
        elif verbose:
            console.print("[dim]→ MANUALS_DIR not set in .env, skipping documentation copy.[/]")
        ```

2.  **Code Review and Cleanup:**
    *   Ensure the new code block is correctly indented and integrated.
    *   Add a comment above the block to explain its purpose (e.g., `# --- Publish Documentation ---`).
    *   Confirm that all required functions (`get_manuals_dir`, `copy_manuals`) are correctly imported at the top of `cli.py`.

### Acceptance Criteria for Phase 1:

*   The `sw-build` command completes without error.
*   When `MANUALS_DIR` is set in the `.env` file and the plugin has a `manual/` directory, the documentation is successfully copied to the target path (`MANUALS_DIR/PluginName/vX.Y.Z/`).
*   The console output displays the status "Publishing documentation..." during the process.

---

## Phase 2: Verification and Documentation

**Goal:** To thoroughly test the fix under various conditions and update the project's documentation to reflect the new, working functionality.

### Key Tasks:

1.  **Conduct Manual Test Cases:**
    *   **Test Case A (Happy Path):**
        -   **Condition:** `MANUALS_DIR` is correctly set, and the plugin being built contains a valid `manual/` directory.
        -   **Expected Result:** The build succeeds, and the manual is copied to the correct destination.
    *   **Test Case B (Configuration Not Set):**
        -   **Condition:** The `MANUALS_DIR` line is commented out or removed from the `.env` file.
        -   **Expected Result:** The build succeeds, and the documentation copying step is gracefully skipped. If run with `-v`, a message indicating the skip is printed.
    *   **Test Case C (No Manual to Copy):**
        -   **Condition:** `MANUALS_DIR` is set, but the plugin being built does *not* have a `manual/` directory.
        -   **Expected Result:** The build succeeds, and the documentation copying step is gracefully skipped with a message (as handled by `manual.py`).

2.  **Update Project `README.md`:**
    *   Navigate to the `README.md` file within the `topdata-package-release-builder` repository.
    *   Review the "Usage" and configuration sections.
    *   Update the description of the `MANUALS_DIR` variable to confirm that it is now an active feature, removing any ambiguity.
    *   Clearly state its purpose: "Set this path to automatically publish the plugin's documentation to your central documentation repository upon release."

3.  **Commit the Changes:**
    *   Commit the updated `cli.py` and `README.md` files to your version control system.
    *   Use a clear and descriptive commit message, such as:
        ```
        feat: Activate automatic documentation publishing
        
        This commit wires the existing manual copying logic into the main CLI.
        The builder now checks for the MANUALS_DIR environment variable and, if set,
        copies the plugin's manual/ directory to the specified central location
        as part of the release process.
        ```

### Acceptance Criteria for Phase 2:

*   All defined test cases pass successfully.
*   The project's `README.md` accurately reflects the new, working functionality.
*   The code changes are committed to the repository, completing the fix.


