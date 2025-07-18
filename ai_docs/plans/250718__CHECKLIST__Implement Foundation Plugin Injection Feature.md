# Checklist: Implement Foundation Plugin Injection Feature

This checklist tracks the implementation of the `--with-foundation` flag to create self-contained plugin releases.

## Phase 1: Configuration and CLI Setup

-   [ ] **`.env.example`:**
    -   [ ] Add `FOUNDATION_PLUGIN_PATH` variable with a placeholder path.
-   [ ] **`topdata_package_release_builder/cli.py`:**
    -   [ ] Add `@click.option('--with-foundation', ...)` to the `build_plugin` command.
    -   [ ] Add `with_foundation` parameter to the `build_plugin` function signature.
    -   [ ] Add logic after `load_env()` to get `FOUNDATION_PLUGIN_PATH` from `os.getenv()`.
    -   [ ] Add validation to ensure the path exists and is a directory if `with_foundation` is `True`.
    -   [ ] Raise a `click.UsageError` if the path is invalid.
    -   [ ] Add a verbose log message to print the `foundation_plugin_path` when found.

## Phase 2: Core Injection Logic

-   [ ] **Create New File:**
    -   [ ] Create the file `topdata_package_release_builder/foundation_injector.py`.
-   [ ] **`foundation_injector.py` - Implement `inject_foundation_code()` function:**
    -   [ ] Define the `DIRECTORIES_TO_INJECT` constant with the correct list of directories.
    -   [ ] The function accepts `target_plugin_build_dir`, `foundation_plugin_path`, and `console`.
    -   [ ] **Read `composer.json`:**
        -   [ ] Construct the path to `composer.json` in the target build directory.
        -   [ ] Load the `composer.json` file as a Python dictionary.
    -   [ ] **Modify `composer.json` (in memory):**
        -   [ ] Check for and **remove** the `topdata/topdata-foundation-sw6` key from the `require` section.
        -   [ ] Extract the base namespace (e.g., `Topdata\TopdataConnectorSW6`) from the `shopware-plugin-class` entry.
        -   [ ] Add the new PSR-4 autoload rule for `src/Foundation/`.
    -   [ ] **File Operations:**
        -   [ ] Create the target directory: `src/Foundation/`.
        -   [ ] Loop through `DIRECTORIES_TO_INJECT`.
        -   [ ] For each directory, copy it from the foundation plugin's source to the target's `src/Foundation/` directory.
        -   [ ] Handle cases where a source directory might not exist.
    -   [ ] **Namespace Rewriting:**
        -   [ ] Call the `rewrite_namespaces_in_dir()` helper function after copying files.
    -   [ ] **Write `composer.json`:**
        -   [ ] Write the modified dictionary back to the `composer.json` file in the build directory.
        -   [ ] Ensure pretty-printing (indent=4) and a trailing newline.
    -   [ ] Add `rich` console output for each major step (e.g., "Removed dependency", "Copied directory", "Rewriting namespaces").
-   [ ] **`foundation_injector.py` - Implement `rewrite_namespaces_in_dir()` helper function:**
    -   [ ] The function accepts `directory`, `old_base`, and `new_base`.
    -   [ ] Use `Path.glob('**/*.php')` to find all PHP files recursively.
    -   [ ] For each file, read its content.
    -   [ ] Use `re.sub()` or `string.replace()` to replace all occurrences of `Topdata\TopdataFoundationSW6` with the new base namespace.
    -   [ ] Write the modified content back to the file only if changes were made.
    -   [ ] Return the total count of modified files.

## Phase 3: Integration into Build Workflow

-   [ ] **`topdata_package_release_builder/cli.py`:**
    -   [ ] Add the import statement: `from .foundation_injector import inject_foundation_code`.
    -   [ ] Inside the `build_plugin` function's `try...with tempfile.TemporaryDirectory()` block:
        -   [ ] Locate the line immediately after `plugin_dir = copy_plugin_files(...)`.
        -   [ ] Add a conditional block: `if with_foundation:`.
        -   [ ] Inside the block, call `inject_foundation_code(plugin_dir, foundation_plugin_path, console=console)`.
        -   [ ] Update the `rich` status message before the call (e.g., `status.update("[bold blue]Injecting foundation code...")`).

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


