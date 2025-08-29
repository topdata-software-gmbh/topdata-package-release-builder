# Implementation Plan: Fix Storefront JS Loading in Variant Plugins

## Phase 1: Analysis and Goal Definition

### 1.1. Goal

The primary goal is to modify the plugin variant creation process to correctly rename the compiled storefront JavaScript asset paths. This will ensure that Shopware 6 can locate and load the JavaScript for the newly created plugin variant (e.g., `FreeTopdataCompareProducts`).

### 1.2. Problem Analysis

The current implementation in `topdata_package_release_builder/variant.py` successfully renames PHP namespaces, class names, and performs string replacements in various files. However, it fails to perform a critical step: renaming the compiled storefront JavaScript directory and its main entry file.

-   **Original Path:** `.../dist/storefront/js/topdata-compare-products/topdata-compare-products.js`
-   **Expected Path for Variant:** `.../dist/storefront/js/free-topdata-compare-products/free-topdata-compare-products.js`

The build process currently leaves the original path intact, causing a mismatch that prevents the storefront JS from being loaded for the variant.

### 1.3. Target File

All modifications will be contained within a single file: `topdata_package_release_builder/variant.py`.

## Phase 2: Code Implementation

This phase involves creating a new helper function to handle the asset renaming and integrating it into the main transformation workflow.

### Step 2.1: Create the Asset Renaming Helper Function

1.  **Instruction:** Define a new private helper function named `_rename_storefront_js_assets`.
2.  **Location:** Place this function within `topdata_package_release_builder/variant.py`, preferably after the `_perform_global_replacement` function for logical grouping.
3.  **Logic:** The function must perform the following actions:
    *   Accept the plugin directory path, original camelCase name, new camelCase name, and the `console` object as arguments.
    *   Convert the camelCase names to kebab-case using the existing `_camel_to_kebab` helper function.
    *   Define the path to the storefront JavaScript `dist` directory (`.../js`).
    *   Add a guard clause to check if this directory exists; if not, log a message and return gracefully.
    *   Construct the full paths for the original asset directory (e.g., `.../js/topdata-compare-products`) and the new target asset directory (e.g., `.../js/free-topdata-compare-products`).
    *   Check if the original asset directory exists.
    *   If it exists, rename the directory to the new name. Log this action.
    *   Inside the newly renamed directory, construct the paths for the original and new main JavaScript files (e.g., `topdata-compare-products.js` -> `free-topdata-compare-products.js`).
    *   Rename the JavaScript file. Log this action.
    *   Include warning logs for edge cases, such as the original asset directory or file not being found.

4.  **Code to Implement:**

    ```python
    def _rename_storefront_js_assets(
        plugin_dir: Path,
        original_name_camel: str,
        new_name_camel: str,
        console: Console
    ) -> None:
        """
        Finds and renames the compiled storefront JavaScript directory and entry file.
        e.g., topdata-compare-products/topdata-compare-products.js -> free-topdata-compare-products/free-topdata-compare-products.js
        """
        original_name_kebab = _camel_to_kebab(original_name_camel)
        new_name_kebab = _camel_to_kebab(new_name_camel)

        js_dist_dir = plugin_dir / "src/Resources/app/storefront/dist/storefront/js"

        if not js_dist_dir.is_dir():
            console.print(f"  [dim]No storefront JS dist directory found at {js_dist_dir}, skipping asset rename.[/dim]")
            return

        original_asset_dir = js_dist_dir / original_name_kebab
        new_asset_dir = js_dist_dir / new_name_kebab

        if original_asset_dir.is_dir():
            # 1. Rename the directory
            original_asset_dir.rename(new_asset_dir)
            console.print(f"  Renamed JS asset directory: {original_asset_dir.name} -> {new_asset_dir.name}")

            # 2. Rename the main JS file inside the new directory
            original_js_file = new_asset_dir / f"{original_name_kebab}.js"
            new_js_file = new_asset_dir / f"{new_name_kebab}.js"
            
            if original_js_file.is_file():
                original_js_file.rename(new_js_file)
                console.print(f"  Renamed JS asset file: {original_js_file.name} -> {new_js_file.name}")
            else:
                console.print(f"  [yellow]Warning:[/yellow] Could not find original JS file to rename: {original_js_file}")
        else:
            console.print(f"  [yellow]Warning:[/yellow] Could not find original JS asset directory to rename: {original_asset_dir}")
    ```

### Step 2.2: Integrate the Helper into the Main Workflow

1.  **Instruction:** Modify the main `transform_to_variant` function to call the newly created `_rename_storefront_js_assets` helper.
2.  **Location:** The call should be placed after other file/directory renaming operations (`_rename_main_php_file`) and before the global text replacement, to ensure path consistency.
3.  **Code to Modify:** Update the `transform_to_variant` function as shown below.

    ```python
    def transform_to_variant(
        plugin_dir: Path,
        original_name: str,
        prefix: str,
        suffix: str,
        console: Console
    ) -> str:
        """
        Transform a plugin into a variant with modified identity.
        
        Args:
            plugin_dir: Path to the plugin directory
            original_name: Original plugin name (e.g., "TopdataMachineTranslationsSW6")
            prefix: Prefix to add (e.g., "Free")
            suffix: Suffix to add
            console: Rich console for logging
            
        Returns:
            The new transformed plugin name
        """
        console.print(f"[bold blue]Transforming plugin to variant...[/]")
        
        # Calculate new identity
        new_name = _calculate_new_name(original_name, prefix, suffix)
        original_namespace = f"Topdata\\{original_name}"
        new_namespace = f"Topdata\\{new_name}"
        original_fqcn = f"Topdata\\{original_name}\\{original_name}"
        new_fqcn = f"Topdata\\{new_name}\\{new_name}"
        
        console.print(f"  Original name: {original_name}")
        console.print(f"  New name: {new_name}")
        console.print(f"  Original namespace: {original_namespace}")
        console.print(f"  New namespace: {new_namespace}")
        
        # Load and modify composer.json
        composer_path = plugin_dir / "composer.json"
        if composer_path.exists():
            _modify_composer_json(
                composer_path, 
                new_name, 
                new_namespace, 
                new_fqcn, 
                prefix, 
                suffix
            )
        
        # Rename main PHP file
        _rename_main_php_file(plugin_dir, original_name, new_name, console)
        
        # Rename storefront JS assets
        _rename_storefront_js_assets(
            plugin_dir,
            original_name,
            new_name,
            console
        )
        
        # Perform global find-replace
        _perform_global_replacement(
            plugin_dir, 
            original_name, 
            new_name, 
            original_namespace, 
            new_namespace,
            console
        )
        
        # Rename root directory
        _rename_root_directory(plugin_dir, original_name, new_name, console)
        
        console.print(f"[green]✓ Plugin transformed to variant: {new_name}[/]")
        return new_name
    ```

## Phase 3: Verification and Review

### 3.1. Self-Correction and Review

After implementing the changes, perform a final review against the following checklist:

-   [ ] The new function `_rename_storefront_js_assets` has been added to `topdata_package_release_builder/variant.py`.
-   [ ] The function correctly converts camelCase to kebab-case for path construction.
-   [ ] The function contains checks for the existence of the directory and file before attempting to rename them.
-   [ ] The function provides clear, informative logging to the console.
-   [ ] The `transform_to_variant` function now includes a call to `_rename_storefront_js_assets`.
-   [ ] The call is placed in the correct logical order (after other renames, before global string replacement).
-   [ ] No other files or logic in the project have been unintentionally altered.

### 3.2. Expected Outcome

After applying these changes, running `sw-build --variant-prefix Free` on a plugin with storefront JavaScript will produce a ZIP archive where:
1.  The plugin's PHP files, namespaces, and metadata are correctly transformed.
2.  The compiled storefront asset directory is renamed (e.g., `.../js/free-topdata-compare-products`).
3.  The main entry JavaScript file within that directory is also renamed (e.g., `free-topdata-compare-products.js`).
4.  When this variant plugin is installed in Shopware 6, the storefront JavaScript will load and execute correctly.

---

This plan provides a complete and verifiable solution to the identified problem. Proceed with implementation.

