Of course. Here is the complete, simplified, and final implementation plan in Markdown format.

---

# **Final Plan: Automate Manuals Repository Publishing**

**Objective:** Enhance the `sw-build` tool to automatically commit and push newly copied documentation to a central Git repository. This plan uses a simplified, single-variable configuration (`MANUALS_DIR`) for clarity and ease of use.

---

### **Phase 1: Configuration & User-Facing Documentation**

**Goal:** Clarify the purpose of the `MANUALS_DIR` variable and update the project's main `README.md` to reflect the new, automated functionality.

1.  **Update `.env.example`**
    *   **File:** `.env.example`
    *   **Action:** Modify the comment for `MANUALS_DIR` to explicitly state that it should be a Git repository for the auto-commit feature to work. We will not add any new variables.
    *   **Change this section:**
        ```dotenv
        # Optional: Path where versioned manual files will be stored
        MANUALS_DIR=/path/to/your/manuals/dir
        ```
    *   **To this:**
        ```dotenv
        # Optional: Path to the local clone of your central manuals git repository.
        # If this path is a valid git repository, new manuals will be automatically
        # copied, committed, and pushed.
        MANUALS_DIR=/path/to/your/local/clone/sw6-plugin-manuals
        ```

2.  **Update `README.md`**
    *   **File:** `README.md`
    *   **Action:** Revise the "Automatic Manual/Documentation Publishing" section to explain the complete, automated workflow.
    *   **Replace the existing section with this content:**

        > ### Automatic Manual/Documentation Publishing
        >
        > The builder can automatically publish a plugin's documentation to a central location. If this location is a Git repository, the tool can also automatically commit and push the changes, creating a fully automated documentation pipeline.
        >
        > **How it works:**
        >
        > 1.  **Central Repository:** You must have a central Git repository to store all your manuals. Clone this repository to your local machine.
        > 2.  **Plugin Structure:** Your plugin must contain a `manual/` directory in its root.
        > 3.  **Configuration:** In your `.env` file, set the `MANUALS_DIR` variable to the absolute path of your **local clone** of the central documentation repository.
        >     ```dotenv
        >     # in .env file
        >     MANUALS_DIR=/path/to/your/central/docs/repo
        >     ```
        > 4.  **Process:** When you run `sw-build`, the tool will:
        >     *   Check if `MANUALS_DIR` is set.
        >     *   Copy the plugin's `manual/` directory into a versioned sub-folder (e.g., `MANUALS_DIR/PluginName/v1.2.3/`).
        >     *   **If `MANUALS_DIR` is a Git repository**, it will then automatically perform a `git pull`, `git add`, `git commit`, and `git push` on that repository.

---

### **Phase 2: Core Logic Implementation**

**Goal:** Add generic, reusable Git functions to `git.py` that can operate on any specified repository path.

1.  **Enhance `git.py`**
    *   **File:** `topdata_package_release_builder/git.py`
    *   **Action:** Add two new functions: `pull_changes_in_repo` and `commit_and_push_changes`.
    *   **Add the following functions to the end of the file:**
        ```python
        def pull_changes_in_repo(repo_path: str, verbose: bool = False, console=None):
            """Pulls the latest changes in the specified repository path."""
            original_dir = os.getcwd()
            try:
                os.chdir(repo_path)
                if verbose and console:
                    console.print(f"[dim]→ Pulling latest changes in {repo_path}...[/]")
                subprocess.check_output(['git', 'pull'], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                if console:
                    console.print(f"[bold red]Error pulling changes in repository '{repo_path}': {e.output.decode()}[/]")
                raise
            finally:
                os.chdir(original_dir)


        def commit_and_push_changes(repo_path: str, commit_message: str, verbose: bool = False, console=None):
            """Adds all changes, commits, and pushes them in the specified repository path."""
            original_dir = os.getcwd()
            try:
                os.chdir(repo_path)
                
                if verbose and console:
                    console.print(f"[dim]→ Staging all changes in {repo_path}...[/]")
                subprocess.check_output(['git', 'add', '.'])
                
                status_output = subprocess.check_output(['git', 'status', '--porcelain']).decode().strip()
                if not status_output:
                    if console:
                        console.print("[dim]→ No changes to commit.[/]")
                    return

                if verbose and console:
                    console.print(f"[dim]→ Committing with message: '{commit_message}'[/]")
                subprocess.check_output(['git', 'commit', '-m', commit_message])
                
                if verbose and console:
                    console.print(f"[dim]→ Pushing changes to remote...[/]")
                subprocess.check_output(['git', 'push'])
                
                if console:
                    console.print("[green]✓ Successfully published changes to git repository.[/]")

            except subprocess.CalledProcessError as e:
                if console:
                    console.print(f"[bold red]Error committing and pushing changes in '{repo_path}': {e.output.decode()}[/]")
                raise
            finally:
                os.chdir(original_dir)
        ```

---

### **Phase 3: Integration into the Build Workflow**

**Goal:** Modify the main `cli.py` script to use the new Git functions after copying manuals, based on whether `MANUALS_DIR` is a Git repository.

1.  **Modify `cli.py`**
    *   **File:** `topdata_package_release_builder/cli.py`
    *   **Action:** Import the new functions and integrate the complete workflow into the `build_plugin` command.

    *   **Step 3.1: Add necessary imports at the top of `cli.py`:**
        ```python
        # from .git import ( ... )
        from .git import (
            get_git_info, check_git_status, stage_changes, commit_and_tag, push_changes,
            pull_changes_in_repo, commit_and_push_changes
        )
        ```

    *   **Step 3.2: Find and replace the manual copying section within the `build_plugin` function:**
        *   **Locate this existing block:**
            ```python
            # ...
            create_archive(output_dir, plugin_name, version, temp_dir, verbose, console)

            # Copy manuals if MANUALS_DIR is configured
            manuals_dir = get_manuals_dir(verbose=verbose, console=console)
            if manuals_dir:
                status.update("[bold blue]Copying manuals...")
                copy_manuals(plugin_name, version, manuals_dir, verbose=verbose, console=console)


            # ---- Get remote config and sync if enabled
            # ...
            ```
        *   **Replace it with the new, enhanced logic:**
            ```python
            # ...
            create_archive(output_dir, plugin_name, version, temp_dir, verbose, console)

            # --- Publish Documentation ---
            manuals_dir = get_manuals_dir(verbose=verbose, console=console)
            if manuals_dir:
                # 1. Copy the files first
                status.update("[bold blue]Copying manuals...")
                copy_manuals(plugin_name, version, manuals_dir, verbose=verbose, console=console)
                
                # 2. Check if the directory is a git repo and then commit/push
                if os.path.isdir(os.path.join(manuals_dir, '.git')):
                    try:
                        status.update("[bold blue]Publishing manual to git repository...")
                        commit_message = f"docs({plugin_name}): Add manual for v{version}"
                        
                        pull_changes_in_repo(manuals_dir, verbose=verbose, console=console)
                        
                        commit_and_push_changes(
                            repo_path=manuals_dir,
                            commit_message=commit_message,
                            verbose=verbose,
                            console=console
                        )
                    except Exception as e:
                        # If git operations fail, we print an error but don't stop the build,
                        # as the primary goal (creating the zip) was successful.
                        console.print(f"[bold red]Warning:[/] Failed to publish manual to git repository: {e}")
                elif verbose:
                    console.print(f"[dim]→ MANUALS_DIR '{manuals_dir}' is not a git repository, skipping auto-commit.[/dim]")

            # ---- Get remote config and sync if enabled
            # ...
            ```

---

### **Phase 4: Verification**

**Goal:** Ensure the new, integrated feature works as expected under various conditions.

1.  **Prepare Test Environment:**
    *   Create a test Git repository (e.g., on your local machine, or a temporary one on GitHub/Bitbucket).
    *   Clone this empty repository to a local path (e.g., `/tmp/test-manuals-repo`).
    *   In your `topdata-package-release-builder` project, set `MANUALS_DIR=/tmp/test-manuals-repo` in your `.env` file.

2.  **Execute Test Cases:**
    *   **Test Case 1 (Happy Path):**
        *   Run `sw-build` for any plugin that has a `manual/` directory.
        *   **Expected Result:** The build completes. The console shows messages for copying, pulling, committing, and pushing. Check the `git log` of your test repository; it should contain a new commit with the message `docs(PluginName): Add manual for vX.Y.Z`. The remote should also have this commit.

    *   **Test Case 2 (No Changes):**
        *   Re-run the same `sw-build` command without changing the plugin version.
        *   **Expected Result:** The build completes. The console should show a "No changes to commit" message after the git staging step. No new commit will be created.

    *   **Test Case 3 (Not a Git Repository):**
        *   Change `MANUALS_DIR` in `.env` to a regular, non-git directory (e.g., `MANUALS_DIR=/tmp/some-other-folder`).
        *   Run `sw-build`.
        *   **Expected Result:** The build completes. The manual files are copied to `/tmp/some-other-folder/PluginName/vX.Y.Z/`. The console shows a message like "...is not a git repository, skipping auto-commit." No git operations are attempted.

