# Implementation Plan: Display Manuals Directory in Initial Verbose Output

**Objective:** To enhance the user experience by displaying the configured `MANUALS_DIR` path in the initial verbose output of the `sw-build` command. This will make its logging consistent with other configurations like `RELEASE_DIR`, allowing users to quickly verify their setup.

## 1. Problem Analysis

Currently, when running `sw-build -v`, the tool immediately logs the `RELEASE_DIR` path, which is helpful for debugging. However, the `MANUALS_DIR` path is only read and processed much later in the script. As a result, its configured value is not visible in the initial startup logs, making it difficult for a user to confirm at a glance that the path is correctly loaded from the `.env` file.

**Current Output (Simplified):**
```
→ Loading environment from: .../.env
→ Reading release directory configuration
→ Found release directory: /path/to/releases
... (many other steps) ...
→ Reading manuals directory configuration
→ Found manuals directory: /path/to/manuals
```

**Desired Output (Simplified):**
```
→ Loading environment from: .../.env
→ Reading manuals directory configuration
→ Found manuals directory: /path/to/manuals
→ Reading release directory configuration
→ Found release directory: /path/to/releases
... (rest of the steps) ...
```

## 2. Proposed Solution

The solution is to refactor the `cli.py` script to call the `get_manuals_dir()` function at the beginning of the `build_plugin` command execution.

1.  **Eager Loading:** The call to `get_manuals_dir()` will be moved to the top of the function, immediately after `load_env()`. This leverages the existing verbose logging within `get_manuals_dir` to print the path early.
2.  **Variable Reuse:** The result of this call will be stored in the `manuals_dir` variable.
3.  **Code Cleanup:** The later, redundant call to `get_manuals_dir()` will be removed, and the script will use the already-populated `manuals_dir` variable for its logic.

This change is simple, low-risk, and directly addresses the requirement without altering the core functionality.

## 3. Implementation Steps

The following changes will be made in the `topdata_package_release_builder/cli.py` file.

### Step 1: Relocate the `get_manuals_dir` Call

Move the function call to the top of the `build_plugin` function to ensure it's executed as part of the initial configuration logging.

**File:** `topdata_package_release_builder/cli.py`

```python
# In the build_plugin function

# ...
def build_plugin(output_dir, source_dir, no_sync, notify_slack, verbose, debug, with_foundation):
    zip_file_rsync_path = None
    """
    ... (docstring) ...
    """
    # Load environment variables
    load_env(verbose=verbose, console=console)

    # ADD THIS BLOCK
    # Get manuals directory config early to show in verbose logs
    manuals_dir = get_manuals_dir(verbose=verbose, console=console)

    # Validate foundation plugin path if injection is requested
    foundation_plugin_path = None
# ...
```

### Step 2: Remove the Redundant Call

Locate the original `get_manuals_dir()` call later in the file (within the "Publish Documentation" section) and remove it, as the `manuals_dir` variable will already be populated.

**File:** `topdata_package_release_builder/cli.py`

**Change this section:**
```python
# --- BEFORE ---
                status.update("[bold blue]Creating ZIP archive...")
                zip_name = f"{plugin_name}-v{version}.zip"
                zip_path = os.path.join(output_dir, zip_name)
                create_archive(output_dir, plugin_name, version, temp_dir, verbose, console)

                # --- Publish Documentation ---
                manuals_dir = get_manuals_dir(verbose=verbose, console=console) # <-- REMOVE THIS LINE
                if manuals_dir:
                    # 1. Copy the files first
                    status.update("[bold blue]Copying manuals...")
                    copy_manuals(plugin_name, version, manuals_dir, source_dir, verbose=verbose, console=console)
```

**To this:**
```python
# --- AFTER ---
                status.update("[bold blue]Creating ZIP archive...")
                zip_name = f"{plugin_name}-v{version}.zip"
                zip_path = os.path.join(output_dir, zip_name)
                create_archive(output_dir, plugin_name, version, temp_dir, verbose, console)

                # --- Publish Documentation ---
                # The 'manuals_dir' variable is now available from the top of the function
                if manuals_dir:
                    # 1. Copy the files first
                    status.update("[bold blue]Copying manuals...")
                    copy_manuals(plugin_name, version, manuals_dir, source_dir, verbose=verbose, console=console)
```

## 4. Verification

1.  Set a valid path for `MANUALS_DIR` in the `.env` file.
2.  Run the build command with the verbose flag: `sw-build -v`.
3.  **Check the console output:** Verify that the `MANUALS_DIR` path is printed near the beginning of the output, along with the `RELEASE_DIR` path.
4.  **Confirm Functionality:** Ensure the build completes successfully and that the documentation is still copied to the correct location, confirming that the rest of the logic works as expected with the refactored code.

