# Refactoring Checklist: Extracting Logic from `cli.py`

This checklist outlines the plan to move business logic from `cli.py` into a new `workflow.py` module, making the command-line interface cleaner and easier to maintain.

---

### Phase 1: Preparation and Scaffolding

*   [ ] **Create New File:** In the `topdata_package_release_builder/` directory, create a new empty file named `workflow.py`.
*   [ ] **Add Boilerplate:** Add the initial docstring and all anticipated `import` statements to the top of `workflow.py`.
*   [ ] **Verification:** Run `sw-build --help` to confirm that adding the new file has not broken anything.

---

### Phase 2: Extract the Versioning Workflow

*   [ ] **Define Function:** In `workflow.py`, define the function signature for `handle_versioning_workflow(...)`.
*   [ ] **Cut Logic from `cli.py`:** In `cli.py`, find the block of code responsible for version selection (starting from `major_version = ...` down to `push_changes(...)`) and **cut** it.
*   [ ] **Paste Logic:** **Paste** the cut code into the `handle_versioning_workflow` function in `workflow.py`.
*   [ ] **Adapt Code:**
    *   [ ] Adjust variable names inside the function to match its parameters (e.g., `version_increment` -> `version_increment_cli`).
    *   [ ] Add `return current_version` for the `VersionBump.NONE` case.
    *   [ ] Add `return new_version_str.lstrip('v')` at the end for successful bumps.
*   [ ] **Update `cli.py`:**
    *   [ ] Add `from .workflow import handle_versioning_workflow` to the imports.
    *   [ ] In the location where the code was cut, add the call to `handle_versioning_workflow(...)`.
*   [ ] **Verification:**
    *   [ ] Test `sw-build` with the interactive versioning prompt.
    *   [ ] Test `sw-build --version-increment patch`.
    *   [ ] Test `sw-build --version-increment none`.
    *   [ ] Confirm that `composer.json` is updated and new git tags are created as expected.

---

### Phase 3: Extract the Manuals Publishing Workflow

*   [ ] **Define Function:** In `workflow.py`, define the function signature for `publish_manuals_workflow(...)`.
*   [ ] **Cut Logic from `cli.py`:** In `cli.py`, find the block of code for publishing manuals (starting with `manuals_dir = get_manuals_dir(...)`) and **cut** it.
*   [ ] **Paste Logic:** **Paste** the cut code into the `publish_manuals_workflow` function in `workflow.py`.
*   [ ] **Update `cli.py`:**
    *   [ ] Add `publish_manuals_workflow` to the `from .workflow import ...` statement.
    *   [ ] In the location where the code was cut, add the call to `publish_manuals_workflow(...)`.
*   [ ] **Verification:**
    *   [ ] Test `sw-build` with `MANUALS_DIR` set in `.env` and a `manual/` directory present in the plugin.
    *   [ ] Confirm files are copied and git operations are executed on the manuals repository.
    *   [ ] Test again without `MANUALS_DIR` set to ensure the step is skipped gracefully.

---

### Phase 4: Final Cleanup

*   [ ] **Review Imports:** Go through `cli.py` and remove any `import` statements that are now unused because the logic was moved to `workflow.py`. (e.g., `InquirerPy`, `bump_version`, `copy_manuals`, etc.).
*   [ ] **Final Verification:** Run a full end-to-end test of `sw-build` using a combination of flags (`--notify-slack`, `--no-sync`, `--variant-prefix`, etc.) to ensure no regressions or `ImportError` exceptions were introduced.

