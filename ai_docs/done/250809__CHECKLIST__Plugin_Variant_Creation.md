## Plugin Variant Creation: Implementation Checklist

### Phase 1: Core Logic (`variant.py`)

-   [x] Create the new file `topdata_package_release_builder/variant.py`.
-   [x] In `variant.py`, define the main function signature: `transform_to_variant(plugin_dir: Path, original_name: str, prefix: str, suffix: str, console) -> str`.
-   [x] **Inside `transform_to_variant`:**
    -   [x] Implement logic to calculate the new plugin name, namespace, and FQCN.
    -   [x] Load the `composer.json` from the `plugin_dir`.
    -   [x] Modify the `name` field in the loaded JSON (e.g., `topdata/plugin` -> `topdata/free-plugin`).
    -   [x] Modify `extra.label` and `extra.description` by prepending the prefix to each language entry.
    -   [x] Modify `extra.shopware-plugin-class` with the new FQCN.
    *   [x] Modify `autoload.psr-4` with the new namespace.
    -   [x] Save the updated data back to `composer.json`.
    -   [x] Implement logic to rename the main plugin PHP file in `src/`.
    -   [x] Implement logic to perform a global find-and-replace for the old namespace and class name in all relevant files (`.php`, `.xml`, `.js`, etc.).
    -   [x] Implement logic to rename the plugin's root directory within the temporary build path.
    -   [x] Ensure the function returns the new, transformed plugin name.

### Phase 2: CLI Integration (`cli.py`)

-   [x] In `topdata_package_release_builder/cli.py`, add the `@click.option('--variant-prefix', ...)` decorator.
-   [x] Add the `@click.option('--variant-suffix', ...)` decorator.
-   [x] In the `build_plugin` function, add a condition to check if `variant_prefix` or `variant_suffix` is provided.
-   [x] **Inside the variant build condition:**
    -   [x] Add a console message indicating the start of the variant build.
    -   [x] Create a second, separate temporary directory using `tempfile.TemporaryDirectory()`.
    -   [x] Call `copy_plugin_files` to copy a fresh version of the plugin to the new temporary directory.
    -   [x] Import `transform_to_variant` from the `variant` module.
    -   [x] Call `transform_to_variant()` on the new copy.
    -   [x] Call `create_release_info()` for the transformed variant.
    -   [x] Call `create_archive()` for the transformed variant.
    -   [x] (Optional) Extend remote sync and Slack notification logic to handle the variant package.

### Phase 3: UX and Documentation

-   [x] In `cli.py`, modify the `_show_success_message` function to display information for both the original and variant packages when a variant is created.
-   [x] In `README.md`, add a new section `### Creating Renamed Variants`.
-   [x] Document the new `--variant-prefix` and `--variant-suffix` flags in the `README.md`.
-   [x] Add a clear usage example to the `README.md`.
-   [x] In `ai_docs/PROJECT_SUMMARY.md`, update the "Key Features" section to include the new variant creation capability.

