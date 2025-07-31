# Plan: Display Documentation Publishing Commands in Release Builder

**Objective:** Extend the `sw-build` tool to display a post-build message. This message will instruct the user on the exact shell commands required to trigger the update and deployment of the documentation via the "Topdata MkDocs Documentation Generator" project.

**Analysis:**
The current release process involves two separate projects:
1.  **`topdata-package-release-builder`**: Builds the plugin and, if `MANUALS_DIR` is configured, copies the plugin's `manual/` directory to a central location.
2.  **`topdata-mkdocs-documentation-generator`**: Consumes the manuals from that central location, builds a static HTML site using MkDocs, and deploys it.

The deployment of the documentation is manually triggered by running `./deploy/deploy.sh` within the documentation generator project. The goal of this plan is to bridge the gap by having the release builder explicitly tell the user how to perform this final step, improving the workflow and reducing ambiguity.

---

## Phase 1: Configuration Setup

**Goal:** Enable the release builder to locate the documentation generator project on the local filesystem.

1.  **Update `.env.example`**
    *   **File:** `topdata-package-release-builder/.env.example`
    *   **Action:** Add a new environment variable to store the path to the documentation generator project. This makes the location configurable without hardcoding it.
    *   **Add the following line:**
        ```dotenv
        # Optional: Path to the documentation generator project to display post-build instructions
        DOCS_GENERATOR_PROJECT_PATH=/topdata/docs-topinfra-de
        ```

2.  **Implement Configuration Getter**
    *   **File:** `topdata_package_release_builder/config.py`
    *   **Action:** Create a new function to safely read this new environment variable.
    *   **Add the following function:**
        ```python
        def get_docs_generator_project_path(verbose=False, console=None):
            """Get the documentation generator project path from environment variables."""
            if verbose and console:
                console.print("[dim]→ Reading documentation generator project path configuration[/]")
            
            docs_path = os.getenv('DOCS_GENERATOR_PROJECT_PATH')
            
            if verbose and console:
                console.print(f"[dim]→ Found docs generator project path: {docs_path or 'Not set'}[/]")
            
            if not docs_path or not os.path.isdir(docs_path):
                if verbose and console and docs_path:
                    console.print(f"[yellow]→ Warning: DOCS_GENERATOR_PROJECT_PATH is set but path not found: {docs_path}[/]")
                return None
            
            return docs_path
        ```

---

## Phase 2: Enhancing the Success Message

**Goal:** Modify the final success message to include the documentation deployment instructions if the relevant paths are configured.

1.  **Update `cli.py` to Display Instructions**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action:** Modify the `_show_success_message` function to check for the new configuration and append a new, formatted panel with the commands.
    *   **Refactor `_show_success_message` as follows:**

        ```python
        # Add this import at the top of cli.py
        from .config import get_docs_generator_project_path
        
        # Modify the existing function
        def _show_success_message(plugin_name, version, zip_name, output_dir, zip_file_rsync_path, slack_status=None):
            """Display success message after build completion."""
            # --- Existing message construction ---
            sync_message = ""
            if zip_file_rsync_path:
                sync_message = f"\n[green]Successfully synced to remote server[/]"
                sync_message += f"\n[green]DL: {_get_download_url(zip_file_rsync_path)}[/]"
            else:
                sync_message = "\n[yellow]Remote sync was disabled[/]"

            slack_message = ""
            if slack_status is True:
                slack_message = "\n[green]Successfully sent Slack notification[/]"
            elif slack_status is False:
                slack_message = "\n[yellow]Failed to send Slack notification[/]"

            # --- Main Success Panel ---
            console.print(Panel(f"""
        [bold green]Plugin successfully built![/]
        Plugin: {plugin_name}
        Version: v{version}
        Archive: {zip_name}
        Location: {output_dir}/{zip_name}{sync_message}{slack_message}
        
        [italic]Note: Built packages are stored in the release directory.[/]
            """, title="Success"))
        
            # --- NEW: Documentation Publishing Instructions ---
            docs_generator_path = get_docs_generator_project_path()
            manuals_dir = get_manuals_dir()
        
            if docs_generator_path and manuals_dir:
                docs_instructions = f"""
        [bold blue]Next Step: Publish Documentation[/]

        To publish the updated manuals online, run the deploy script
        in the documentation project:

        [bold white on blue] cd {docs_generator_path} [/]
        [bold white on blue] ./deploy/deploy.sh [/]
                """
                console.print(Panel(docs_instructions, title="Documentation", border_style="blue"))

        ```

---

## Phase 3: Verification

**Goal:** Ensure the new instructions appear correctly and only when intended.

1.  **Set up Environment:**
    *   In your `.env` file for the release builder, ensure both `MANUALS_DIR` and the new `DOCS_GENERATOR_PROJECT_PATH` are set to valid paths.

2.  **Run a Build:**
    *   Execute the `sw-build` command for any test plugin that contains a `manual/` directory.

3.  **Check the Output:**
    *   After the standard "Success" panel, verify that a new blue panel titled "Documentation" appears.
    *   Confirm that the commands shown in the panel are correct and use the path you configured in `DOCS_GENERATOR_PROJECT_PATH`.

4.  **Test the Negative Case:**
    *   Comment out or remove the `DOCS_GENERATOR_PROJECT_PATH` from your `.env` file.
    *   Run the build again.
    *   Verify that the "Documentation" panel **does not** appear.

---
## Expected Outcome

When the build is complete and the necessary environment variables are set, the user will see the following output in their terminal in addition to the existing success message:

```
╭──────────────────────────────────────── Documentation ────────────────────────────────────────╮
│                                                                                           │
│                      Next Step: Publish Documentation                                     │
│                                                                                           │
│  To publish the updated manuals online, run the deploy script                             │
│  in the documentation project:                                                            │
│                                                                                           │
│   cd /topdata/docs-topinfra-de                                                            │
│   ./deploy/deploy.sh                                                                      │
│                                                                                           │
╰───────────────────────────────────────────────────────────────────────────────────────────╯
```

