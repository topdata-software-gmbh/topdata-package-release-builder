# Plan: Implement Foundation Plugin Injection for Self-Contained Releases

**Objective:** Enhance the `sw-build` tool to automatically inject code from the `TopdataFoundationSW6` plugin into another plugin's build package. This process will involve copying necessary source files, rewriting PHP namespaces, and updating `composer.json` to remove the explicit dependency, making the final ZIP package self-contained and compliant with Shopware Store requirements.

**Target Audience:** AI Coding Agent

**Pre-computation Analysis:**
*   The agent must have access to the complete codebase for `topdata-package-release-builder`, `topdata-foundation-sw6`, and the example target plugin `topdata-connector-sw6`.
*   The core logic will be encapsulated in a new module: `foundation_injector.py`.
*   The main CLI file, `cli.py`, will be modified to include a new option and orchestrate the injection process.

---

## Phase 1: Configuration and CLI Setup

**Goal:** Prepare the build tool to accept the new injection command and locate the foundation plugin source.

1.  **Update Environment Configuration:**
    *   **File:** `.env.example`
    *   **Action:** Append a new configuration variable to specify the path to the foundation plugin. This informs users of the new requirement.
    *   **Add the following line:**
        ```dotenv
        # Optional: Path to the TopdataFoundationSW6 plugin for code injection
        FOUNDATION_PLUGIN_PATH=/path/to/your/workspace/topdata-foundation-sw6
        ```

2.  **Enhance the CLI Command:**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action 1: Add the `--with-foundation` CLI option.** Use the `@click.option` decorator.
    *   **Action 2: Update the `build_plugin` function signature** to accept the new `with_foundation` parameter.
    *   **Action 3: Add logic to validate the `FOUNDATION_PLUGIN_PATH`** when the flag is used. This ensures the script fails early if the configuration is incorrect.

    *   **Modify `cli.py` as follows:**
        ```python
        # In the options section for the build_plugin command
        @click.option('--with-foundation', is_flag=True, help='Inject TopdataFoundationSW6 code into the plugin package.')

        # In the function signature
        def build_plugin(output_dir, source_dir, no_sync, notify_slack, verbose, debug, with_foundation):
            # ... function body ...
        ```
        ```python
        # Immediately after the `load_env(...)` call
        # Load environment variables
        load_env(verbose=verbose, console=console)

        # Validate foundation plugin path if injection is requested
        foundation_plugin_path = None
        if with_foundation:
            foundation_plugin_path = os.getenv('FOUNDATION_PLUGIN_PATH')
            if not foundation_plugin_path or not os.path.isdir(foundation_plugin_path):
                raise click.UsageError(
                    "--with-foundation flag was used, but FOUNDATION_PLUGIN_PATH is not set correctly in .env\n"
                    f"Path configured: {foundation_plugin_path}"
                )
            if verbose:
                console.print(f"[dim]→ Foundation plugin path: {foundation_plugin_path}[/dim]")
        ```

## Phase 2: Implement the Core Injection Logic

**Goal:** Create a new, dedicated module to handle the complex process of copying, rewriting, and reconfiguring the plugin code.

1.  **Create New Module:**
    *   **File:** `topdata_package_release_builder/foundation_injector.py`
    *   **Action:** Create this new file and add the complete code below. This module will contain all logic for the injection process.

2.  **Implement Injection and Rewriting Logic:**
    *   **File:** `topdata_package_release_builder/foundation_injector.py`
    *   **Action:** Populate the file with the following Python code. The code is commented to explain each step of the process.

    ```python
    import os
    import re
    import shutil
    import json
    from pathlib import Path

    # --- CONFIGURATION ---
    # Defines which directories from the foundation plugin should be injected.
    # This provides precise control, avoiding unnecessary files like migrations.
    DIRECTORIES_TO_INJECT = [
        'Command',
        'Constants',
        'Core/Content/TopdataReport',
        'DataStructure',
        'DTO',
        'Exception',
        'Helper',
        'Service',
        'Twig',
        'Util',
    ]

    def inject_foundation_code(target_plugin_build_dir: str, foundation_plugin_path: str, console=None):
        """
        Copies foundation code, rewrites namespaces, removes dependency, and configures autoloading.

        Args:
            target_plugin_build_dir: The temporary build directory of the target plugin.
            foundation_plugin_path: The source path of the TopdataFoundationSW6 plugin.
            console: Rich console instance for output.
        """
        if console:
            console.print(f"[bold blue]Injecting foundation code from:[/] {foundation_plugin_path}")

        foundation_src_path = Path(foundation_plugin_path) / 'src'
        target_foundation_dir = Path(target_plugin_build_dir) / 'src' / 'Foundation'
        target_foundation_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Read the target plugin's composer.json
        composer_path = Path(target_plugin_build_dir) / 'composer.json'
        with open(composer_path, 'r', encoding='utf-8') as f:
            composer_data = json.load(f)

        # Step 2: REMOVE the foundation plugin dependency from the 'require' section
        if 'require' in composer_data and 'topdata/topdata-foundation-sw6' in composer_data['require']:
            del composer_data['require']['topdata/topdata-foundation-sw6']
            if console:
                console.print("[dim]→ Removed '[bold cyan]topdata/topdata-foundation-sw6[/bold cyan]' from composer requirements.[/dim]")

        # Step 3: Get Target Plugin's Namespace for rewriting
        plugin_class = composer_data['extra']['shopware-plugin-class']
        target_namespace_base = "\\".join(plugin_class.split('\\')[:-1])

        if console:
            console.print(f"[dim]→ Target plugin namespace base: [bold cyan]{target_namespace_base}[/bold cyan][/dim]")

        # Step 4: Copy configured directories from foundation plugin
        for dir_name in DIRECTORIES_TO_INJECT:
            source_dir = foundation_src_path / dir_name
            dest_dir = target_foundation_dir / Path(dir_name)
            if source_dir.is_dir():
                shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
                if console:
                    console.print(f"[dim]→ Copied directory: [green]{dir_name}[/green][/dim]")
            elif console:
                console.print(f"[dim]→ [yellow]Warning:[/yellow] Source directory not found, skipping: {source_dir}[/dim]")

        # Step 5: Rewrite namespaces in all copied PHP files
        old_namespace = "Topdata\\TopdataFoundationSW6"
        new_namespace = f"{target_namespace_base}\\Foundation"
        if console:
            console.print(f"[dim]→ Rewriting namespaces from '{old_namespace}' to '{new_namespace}'[/dim]")

        files_rewritten = rewrite_namespaces_in_dir(target_foundation_dir, old_namespace, new_namespace)

        if console:
            console.print(f"[dim]→ Rewrote namespaces in {files_rewritten} files.[/dim]")

        # Step 6: Update composer.json to ADD autoloading for the new Foundation directory
        autoload_key = f"{target_namespace_base}\\Foundation\\"
        composer_data.setdefault('autoload', {}).setdefault('psr-4', {})[autoload_key] = "src/Foundation/"

        # Step 7: Write all changes back to composer.json
        with open(composer_path, 'w', encoding='utf-8') as f:
            json.dump(composer_data, f, indent=4, ensure_ascii=False)
            f.write('\n')  # Add trailing newline for POSIX compliance

        if console:
            console.print("[green]✓ Foundation code injected and composer.json updated.[/green]")


    def rewrite_namespaces_in_dir(directory: Path, old_base: str, new_base: str) -> int:
        """
        Recursively finds .php files and replaces namespace and use statements.
        """
        count = 0
        for php_file in directory.glob('**/*.php'):
            content = php_file.read_text(encoding='utf-8')
            
            # This regex is a simple but effective replacement for the base namespace.
            pattern = re.compile(re.escape(old_base))
            
            new_content = pattern.sub(new_base, content)
            
            if new_content != content:
                php_file.write_text(new_content, encoding='utf-8')
                count += 1
                
        return count
    ```

## Phase 3: Integrate Injector into the Build Workflow

**Goal:** Trigger the new injection logic at the correct point in the existing build process.

1.  **Modify CLI Workflow:**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action 1: Import the new `inject_foundation_code` function.**
    *   **Action 2: Call the function** within the `try...with tempfile.TemporaryDirectory()` block, immediately after the plugin files have been copied.

    *   **Modify `cli.py` as follows:**
        ```python
        # Near the top with other imports
        from .foundation_injector import inject_foundation_code

        # Inside the build_plugin function, within the `with tempfile.TemporaryDirectory() as temp_dir:` block
        # ...
            with tempfile.TemporaryDirectory() as temp_dir:
                status.update("[bold blue]Copying plugin files...")
                if verbose:
                    console.print(f"[dim]→ Using temporary directory: {temp_dir}[/dim]")
                plugin_dir = copy_plugin_files(temp_dir, plugin_name, source_dir=source_dir, verbose=verbose, console=console)

                # --- INJECTION STEP ---
                if with_foundation:
                    status.update("[bold blue]Injecting foundation code...")
                    inject_foundation_code(plugin_dir, foundation_plugin_path, console=console)
                # --- END INJECTION STEP ---

                status.update("[bold blue]Creating release info...")
        # ...
        ```

## Phase 4: Verification and Documentation

**Goal:** Ensure the feature works as expected and document it for future use.

1.  **Manual Verification Steps:**
    *   Execute the build command on the `topdata-connector-sw6` plugin: `sw-build -v --with-foundation`.
    *   Unzip the generated package from your `RELEASE_DIR`.
    *   **Verify Directory Structure:** Confirm the existence of the `src/Foundation/` directory with its subdirectories (`Util`, `Service`, etc.).
    *   **Verify `composer.json`:**
        *   Open the `composer.json` file inside the unzipped package.
        *   Confirm that the `"require"` section **does not** contain `"topdata/topdata-foundation-sw6"`.
        *   Confirm that the `"autoload"` -> `"psr-4"` section **does** contain an entry similar to `"Topdata\\TopdataConnectorSW6\\Foundation\\": "src/Foundation/"`.
    *   **Verify Namespace Rewriting:**
        *   Open a copied file, e.g., `src/Foundation/Util/CliLogger.php`, and confirm its namespace is now `namespace Topdata\TopdataConnectorSW6\Foundation\Util;`.
        *   Open a file from the original plugin that uses a foundation class, e.g., `src/Command/Command_Import.php`. Confirm its `use` statements have been rewritten to `use Topdata\TopdataConnectorSW6\Foundation\Util\CliLogger;` and that it extends `...Foundation\Command\AbstractTopdataCommand`.

2.  **Update Documentation:**
    *   **File:** `README.md`
    *   **Action:** Add a section explaining the dependency injection feature for creating self-contained plugins, mentioning the `--with-foundation` flag and the required `FOUNDATION_PLUGIN_PATH` environment variable.
    *   **File:** `ai_docs/PROJECT_SUMMARY.md`
    *   **Action:** Update the summary to reflect this new build capability, describing how it solves the Shopware Store compliance issue.

---
