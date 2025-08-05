# **Implementation Plan: Smarter Foundation Plugin Injection**

**Objective:** To refactor the `sw-build` tool to make the foundation plugin injection process more automated and user-friendly. The goal is to eliminate the need for cumbersome command-line variables and flags in the standard workflow by implementing intelligent defaults and automatic dependency detection.

**Current Workflow:**
`FOUNDATION_PLUGIN_PATH=../topdata-foundation-sw6 sw-build --with-foundation`

**Target Workflow (Standard Case):**
`sw-build`

---

## **Phase 1: Implement Smart Foundation Path Resolution**

**Goal:** Modify the tool to automatically locate the `topdata-foundation-sw6` plugin. It will first check for an environment variable override, and if not found, it will look in a default relative location (`../topdata-foundation-sw6`).

### **Key Tasks:**

1.  **Create a Path-Finding Helper Function in `cli.py`**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action:** Add a new private helper function, `_get_foundation_path`, to encapsulate the logic for finding the foundation plugin's source directory. This keeps the main `build_plugin` function cleaner.
    *   **Code to Add:**
        ```python
        # In topdata_package_release_builder/cli.py, before the build_plugin command

        from pathlib import Path

        def _get_foundation_path(source_dir: str, verbose: bool, console) -> str | None:
            """
            Determines the path to the foundation plugin, prioritizing environment variables
            over a default relative path.
            """
            # 1. Check for an explicit override from the environment variable.
            foundation_path_env = os.getenv('FOUNDATION_PLUGIN_PATH')
            if foundation_path_env:
                if verbose:
                    console.print("[dim]→ Using FOUNDATION_PLUGIN_PATH from environment.[/dim]")
                path_to_check = Path(foundation_path_env)
            else:
                # 2. If no override, construct the default path relative to the target plugin.
                # e.g., if source_dir is '.../my-plugin', this will be '.../topdata-foundation-sw6'
                if verbose:
                    console.print("[dim]→ FOUNDATION_PLUGIN_PATH not set, checking default relative path.[/dim]")
                default_path = Path(source_dir).resolve().parent / 'topdata-foundation-sw6'
                path_to_check = default_path

            # 3. Validate the determined path.
            if path_to_check.is_dir():
                if verbose:
                    console.print(f"[dim]→ Valid foundation plugin path found: {path_to_check.resolve()}[/dim]")
                return str(path_to_check.resolve())

            if verbose:
                console.print(f"[yellow]→ Foundation plugin not found at checked path: {path_to_check}[/yellow]")
            return None
        ```

2.  **Refactor `cli.py` to Prepare for the Helper**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action:** Temporarily comment out the existing logic that validates `FOUNDATION_PLUGIN_PATH` inside the `if with_foundation:` block. This logic will be replaced in the next phases by the new helper function.

### **Acceptance Criteria:**

*   The new `_get_foundation_path` function is present in `cli.py`.
*   The function correctly returns a path when `FOUNDATION_PLUGIN_PATH` is set in the `.env` file.
*   The function correctly calculates and returns the default path (`../topdata-foundation-sw6`) when the environment variable is not set.

---

## **Phase 2: Automatic Injection Based on `composer.json`**

**Goal:** Make the foundation injection trigger automatically if `topdata/topdata-foundation-sw6` is listed as a dependency in the target plugin's `composer.json`. The `--with-foundation` flag will now serve as an explicit override to force injection.

### **Key Tasks:**

1.  **Create a Dependency Checker in `plugin.py`**
    *   **File:** `topdata_package_release_builder/plugin.py`
    *   **Action:** Add a new function to check for the foundation dependency. This keeps `composer.json` parsing logic within the `plugin` module.
    *   **Code to Add:**
        ```python
        # In topdata_package_release_builder/plugin.py

        def has_foundation_dependency(source_dir='.', verbose=False, console=None) -> bool:
            """Checks if the plugin's composer.json requires the foundation plugin."""
            composer_path = Path(source_dir) / 'composer.json'
            if not composer_path.is_file():
                return False

            try:
                with open(composer_path, 'r', encoding='utf-8') as f:
                    composer_data = json.load(f)

                has_dep = 'topdata/topdata-foundation-sw6' in composer_data.get('require', {})
                if verbose and console:
                    console.print(f"[dim]→ Checking for foundation dependency in composer.json: {'[green]Yes[/green]' if has_dep else 'No'}[/dim]")
                return has_dep
            except (json.JSONDecodeError, IOError):
                if verbose and console:
                    console.print(f"[yellow]Warning: Could not parse {composer_path}[/yellow]")
                return False
        ```

2.  **Integrate the Full Injection Logic into `cli.py`**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action:** Replace the old `if with_foundation:` block entirely with a new, smarter logic block that uses the functions created in Phase 1 and 2.
    *   **Import the new function:**
        ```python
        from .plugin import (
            get_plugin_info,
            copy_plugin_files,
            create_archive,
            verify_compiled_files,
            has_foundation_dependency, # <-- Add this
        )
        ```
    *   **Replace the logic:** Find the section marked `--- INJECTION STEP ---` and replace the `if with_foundation:` block with the following:
        ```python
        # In topdata_package_release_builder/cli.py, inside build_plugin()

        # --- INJECTION STEP ---
        # Determine if we need to inject foundation code, either by flag or by dependency.
        is_forced = with_foundation
        has_dep = has_foundation_dependency(source_dir, verbose=verbose, console=console)
        
        should_inject_foundation = is_forced or has_dep

        if should_inject_foundation:
            if is_forced and not has_dep:
                console.print("[yellow]Note:[/] Forcing foundation injection via --with-foundation flag.")
            
            status.update("[bold blue]Locating foundation plugin...")
            foundation_plugin_path = _get_foundation_path(source_dir, verbose, console)
            
            if not foundation_plugin_path:
                raise click.UsageError(
                    "Foundation injection is required, but the foundation plugin path could not be found.\n"
                    "1. Place it at '../topdata-foundation-sw6' relative to your plugin, or\n"
                    "2. Set the FOUNDATION_PLUGIN_PATH in your .env file."
                )

            status.update("[bold blue]Injecting foundation code...")
            from .foundation_injector import inject_foundation_code
            inject_foundation_code(plugin_dir, foundation_plugin_path, console=console)
        # --- END INJECTION STEP ---
        ```

### **Acceptance Criteria:**

*   `sw-build` on a plugin *with* the dependency automatically triggers the injection process.
*   `sw-build` on a plugin *without* the dependency does *not* trigger injection.
*   `sw-build --with-foundation` on a plugin *without* the dependency *forces* the injection process.
*   If injection is required but the foundation plugin cannot be found (neither at default path nor via env var), the build aborts with a clear error message.

---

## **Phase 3: Final Touches and Documentation**

**Goal:** Clean up the implementation, update user-facing help text, and document the new, simplified workflow.

### **Key Tasks:**

1.  **Update CLI Help Text**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action:** Modify the help text for the `--with-foundation` option to reflect its new purpose as a "force" flag.
    *   **Change This:**
        ```python
        @click.option('--with-foundation', is_flag=True, help='Inject TopdataFoundationSW6 code into the plugin package.')
        ```
    *   **To This:**
        ```python
        @click.option('--with-foundation', is_flag=True, help='Force injection of foundation code, even if not in composer.json.')
        ```

2.  **Update `README.md`**
    *   **File:** `README.md`
    *   **Action:** Add a new section or update an existing one to describe the new, intelligent foundation injection feature.
    *   **Suggested Content:**
        > ### Smart Foundation-Plugin Injection
        >
        > The `sw-build` tool simplifies the process of creating self-contained plugins that depend on `topdata/topdata-foundation-sw6`.
        >
        > **Automatic Detection:**
        > If your plugin's `composer.json` lists `topdata/topdata-foundation-sw6` as a dependency, the build tool will automatically:
        > 1.  Locate the foundation plugin at the default relative path (`../topdata-foundation-sw6`).
        > 2.  Inject the necessary code, rewrite namespaces, and remove the dependency from the final package, making it ready for the Shopware Store.
        >
        > **Overriding the Path:**
        > If your foundation plugin is located elsewhere, you can specify its path in your `.env` file:
        > `FOUNDATION_PLUGIN_PATH=/path/to/your/topdata-foundation-sw6`
        >
        > **Forcing Injection:**
        > To inject the foundation code into a plugin that does *not* list it as a dependency, use the `--with-foundation` flag:
        > `sw-build --with-foundation`

3.  **Perform a Final Verification**
    *   Run `sw-build` against a test plugin under the following conditions:
        *   **Standard Case:** Plugin has foundation dependency, no flags or env vars set. -> **Expect:** Success, using default path.
        *   **Override Case:** Plugin has dependency, `FOUNDATION_PLUGIN_PATH` is set. -> **Expect:** Success, using env var path.
        *   **No-op Case:** Plugin does *not* have dependency. -> **Expect:** Success, no injection attempted.
        *   **Force Case:** Plugin does *not* have dependency, run with `--with-foundation`. -> **Expect:** Success, injection is forced.
        *   **Failure Case:** Plugin has dependency, but foundation plugin cannot be found. -> **Expect:** Build aborts with a helpful error.

### **Acceptance Criteria:**
*   The CLI help text is updated and accurate.
*   The `README.md` clearly explains the new, simplified workflow.
*   All verification scenarios pass as expected, confirming the logic is robust.

