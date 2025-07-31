# Checklist: Implement Foundation Plugin Injection Feature

This checklist tracks the implementation of the `--with-foundation` flag to create self-contained plugin releases.

## Phase 1: Configuration and CLI Setup

-   [x] **`.env.example`:**
    -   [x] Add `FOUNDATION_PLUGIN_PATH` variable with a placeholder path.
-   [ ] **`topdata_package_release_builder/cli.py`:**
    -   [x] Add `@click.option('--with-foundation', ...)` to the `build_plugin` command.
    -   [x] Add `with_foundation` parameter to the `build_plugin` function signature.
    -   [x] Add logic after `load_env()` to get `FOUNDATION_PLUGIN_PATH` from `os.getenv()`.
    -   [x] Add validation to ensure the path exists and is a directory if `with_foundation` is `True`.
    -   [x] Raise a `click.UsageError` if the path is invalid.
    -   [x] Add a verbose log message to print the `foundation_plugin_path` when found.

## Phase 2: Core Injection Logic

-   [ ] **Create New File:**
    -   [x] Create the file `topdata_package_release_builder/foundation_injector.py`.
-   [x] **`foundation_injector.py` - Implement `inject_foundation_code()` function:**
    -   [x] Define the `DIRECTORIES_TO_INJECT` constant with the correct list of directories.
    -   [x] The function accepts `target_plugin_build_dir`, `foundation_plugin_path`, and `console`.
    -   [x] **Read `composer.json`:**
        -   [x] Construct the path to `composer.json` in the target build directory.
        -   [x] Load the `composer.json` file as a Python dictionary.
    -   [x] **Modify `composer.json` (in memory):**
        -   [x] Check for and **remove** the `topdata/topdata-foundation-sw6` key from the `require` section.
        -   [x] Extract the base namespace (e.g., `Topdata\\TopdataConnectorSW6`) from the `shopware-plugin-class` entry.
        -   [x] Add the new PSR-4 autoload rule for `src/Foundation/`.
    -   [x] **File Operations:**
        -   [x] Create the target directory: `src/Foundation/`.
        -   [x] Loop through `DIRECTORIES_TO_INJECT`.
        -   [x] For each directory, copy it from the foundation plugin's source to the target's `src/Foundation/` directory.
        -   [x] Handle cases where a source directory might not exist.
    -   [x] **Namespace Rewriting:**
        -   [x] Call the `rewrite_namespaces_in_dir()` helper function after copying files.
    -   [x] **Write `composer.json`:**
        -   [x] Write the modified dictionary back to the `composer.json` file in the build directory.
        -   [x] Ensure pretty-printing (indent=4) and a trailing newline.
    -   [x] Add `rich` console output for each major step (e.g., "Removed dependency", "Copied directory", "Rewriting namespaces").
-   [x] **`foundation_injector.py` - Implement `rewrite_namespaces_in_dir()` helper function:**
    -   [x] The function accepts `directory`, `old_base`, and `new_base`.
    -   [x] Use `Path.glob('**/*.php')` to find all PHP files recursively.
    -   [x] For each file, read its content.
    -   [x] Use `re.sub()` or `string.replace()` to replace all occurrences of `Topdata\\TopdataFoundationSW6` with the new base namespace.
    -   [x] Write the modified content back to the file only if changes were made.
    -   [x] Return the total count of modified files.

## Phase 3: Integration into Build Workflow

-   [ ] **`topdata_package_release_builder/cli.py`:**
    -   [x] Add the import statement: `from .foundation_injector import inject_foundation_code`.
    -   [x] Inside the `build_plugin` function's `try...with tempfile.TemporaryDirectory()` block:
        -   [x] Locate the line immediately after `plugin_dir = copy_plugin_files(...)`.
        -   [x] Add a conditional block: `if with_foundation:`.
        -   [x] Inside the block, call `inject_foundation_code(plugin_dir, foundation_plugin_path, console=console)`.
        -   [x] Update the `rich` status message before the call (e.g., `status.update("[bold blue]Injecting foundation code...")`).

## Phase 4: Verification and Documentation

-   [ ] **Manual Verification:**
    -   [ ] Run `sw-build -v --with-foundation` on a test plugin (e.g., `topdata-connector-sw6`).
    -   [ ] **Unzip the Result:** Extract the contents of the generated `.zip` file.
    -   [ ] **Check `composer.json`:**
        -   [ ] Verify `topdata/topdata-foundation-sw6` is **absent** from `require`.
        -   [ ] Verify the new PSR-4 rule for `...\\Foundation\\` is **present** in `autoload`.
    -   [ ] **Check File Structure:**
        -   [ ] Verify the `src/Foundation` directory and its contents exist.
    -   [ ] **Check Namespaces:**
        -   [ ] Open a file like `src/Foundation/Util/CliLogger.php` and confirm its namespace has been rewritten.
        -   [ ] Open a file from the original plugin like `src/Command/Command_Import.php` and confirm its `use` statements have been rewritten.
-   [ ] **Documentation:**
    -   [ ] **`README.md`:** Update to explain the new `--with-foundation` feature and the `FOUNDATION_PLUGIN_PATH` `.env` variable.
    -   [ ] **`ai_docs/PROJECT_SUMMARY.md`:** Update to describe the new build capability that ensures Shopware Store compliance.


