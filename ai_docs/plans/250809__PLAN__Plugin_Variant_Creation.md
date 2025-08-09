# Implementation Plan: Plugin Variant Creation

This plan outlines the steps required to enhance the `sw-build` tool, enabling it to generate a second, renamed ZIP package (a "variant") from a single plugin source. This allows for creating alternate versions, such as a "Free" version, from the main codebase.

## Project Goal

To modify the `sw-build` CLI tool to optionally create a primary release ZIP and a secondary, "variant" release ZIP. The variant will have its core identifiers—including its PHP namespace, class name, and `composer.json` metadata—programmatically transformed based on a user-provided prefix or suffix.

## Phase 1: Develop the Core Variant Transformation Logic

**Objective:** Isolate all transformation logic into a new, dedicated module for clarity, testability, and maintainability.

1.  **Create New Module: `variant.py`**
    *   Create a new file: `topdata_package_release_builder/variant.py`.
    *   This module will house all functions related to transforming a plugin's identity.

2.  **Implement the Main Transformation Function**
    *   Define a primary function within `variant.py`:
        ```python
        def transform_to_variant(
            plugin_dir: Path,
            original_name: str,
            prefix: str,
            suffix: str,
            console
        ) -> str:
            # ... implementation ...
            return new_plugin_name
        ```

3.  **Detailed Transformation Steps within `transform_to_variant`:**
    *   **A. Calculate New Identity:**
        *   Based on the `original_name` (e.g., `TopdataMachineTranslationsSW6`), `prefix` (e.g., `Free`), and `suffix`, calculate the new identifiers:
            *   **New Plugin Name:** `FreeTopdataMachineTranslationsSW6`
            *   **Original Namespace:** `Topdata\\TopdataMachineTranslationsSW6`
            *   **New Namespace:** `Topdata\\FreeTopdataMachineTranslationsSW6`
            *   **Original FQCN:** `Topdata\\TopdataMachineTranslationsSW6\\TopdataMachineTranslationsSW6`
            *   **New FQCN:** `Topdata\\FreeTopdataMachineTranslationsSW6\\FreeTopdataMachineTranslationsSW6`

    *   **B. Modify `composer.json` Metadata:**
        *   Load the `composer.json` file.
        *   Apply the following transformation rules:
            *   **`name`:** Prepend the lower-cased prefix/suffix to the package part.
                *   *From:* `topdata/machine-translations`
                *   *To:* `topdata/free-machine-translations`
            *   **`extra.label`:** For each language, prepend the prefix/suffix in a consistent format (e.g., `[FREE]`).
                *   *From:* `"Topdata Machine Translations"`
                *   *To:* `"[FREE] Topdata Machine Translations"`
            *   **`extra.description`:** For each language, prepend the prefix/suffix in the same format.
                *   *From:* `"A Shopware 6 plugin..."`
                *   *To:* `"[FREE] A Shopware 6 plugin..."`
            *   **`extra.shopware-plugin-class`:** Update with the new FQCN.
            *   **`autoload.psr-4`:** Update the key with the new namespace.
        *   Save the modified `composer.json` file.

    *   **C. Rename Main Plugin File:**
        *   Rename the main plugin PHP file in the `src/` directory.
        *   *Example:* `src/TopdataMachineTranslationsSW6.php` -> `src/FreeTopdataMachineTranslationsSW6.php`.

    *   **D. Perform Global Content Replacement:**
        *   Recursively scan all text-based files (`.php`, `.xml`, `.js`, `.twig`, etc.).
        *   In each file, replace all occurrences of the original namespace and plugin name with their new counterparts.

    *   **E. Rename Root Directory:**
        *   Rename the plugin's root folder within the temporary build directory to reflect the new plugin name. This ensures the correct top-level directory inside the final ZIP archive.

## Phase 2: Integrate Variant Creation into the CLI and Build Workflow

**Objective:** Expose the new functionality to the user via CLI flags and orchestrate the variant build process within the main script.

1.  **Add New CLI Options in `cli.py`**
    *   Decorate the `build_plugin` function with new `@click.option` flags:
        ```python
        @click.option('--variant-prefix', default=None, help='Add a prefix to create a renamed variant package (e.g., "Free").')
        @click.option('--variant-suffix', default=None, help='Add a suffix to create a renamed variant package.')
        ```

2.  **Update the Main Build Workflow in `cli.py`**
    *   After the primary package ZIP is successfully created, check if `--variant-prefix` or `--variant-suffix` was provided.
    *   If a variant is requested:
        1.  Print a status message to the console (e.g., `[bold blue]Building variant package...[/]`).
        2.  Create a **new, separate temporary directory** for the variant build.
        3.  Call `copy_plugin_files` again to get a fresh, unaltered copy of the plugin source in the new temp directory.
        4.  Import and call the `transform_to_variant` function from the `variant` module on the new copy.
        5.  Generate a new `release_info.txt` file for the variant.
        6.  Call `create_archive` using the transformed plugin name and version to create the second ZIP file.
        7.  Optionally, if sync and notifications are enabled, run these steps for the newly created variant package as well, generating a separate remote path and Slack message.

## Phase 3: Refine User Experience and Documentation

**Objective:** Ensure the new feature is clearly documented and that the tool's output is informative.

1.  **Enhance Final Success Message**
    *   Modify the `_show_success_message` function in `cli.py`.
    *   If a variant was built, update the final output `Panel` to display the details of **both** the original and the variant packages, including their respective archive names and locations.

2.  **Update `README.md`**
    *   Add a new section titled `### Creating Renamed Variants`.
    *   Explain the purpose of the feature.
    *   Document the new `--variant-prefix` and `--variant-suffix` flags.
    *   Provide a clear usage example:
        ```bash
        # Creates the standard plugin and a variant with "Free" prepended to its name
        sw-build --variant-prefix Free
        ```

3.  **Update `ai_docs/PROJECT_SUMMARY.md`**
    *   In the "Key Features" section, add a new bullet point describing the variant creation capability to ensure AI assistants have the most current project context.

