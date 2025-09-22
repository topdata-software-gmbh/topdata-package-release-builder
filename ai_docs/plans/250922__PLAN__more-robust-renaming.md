### **Objective**

The goal is to modify the `topdata-package-release-builder` tool to correctly rename JavaScript assets and their references when creating a plugin variant. This will be achieved by making the asset discovery process dynamic and the string replacement logic more comprehensive.

---

### **Phase 1: Core Logic Enhancement in `variant.py`**

This phase focuses on updating the Python script responsible for creating plugin variants to be more intelligent and robust.

#### **Step 1.1: Implement Dynamic JS Asset Directory Discovery**

The current implementation assumes a fixed naming convention for the JS asset directory. This step will replace that with a dynamic discovery mechanism.

*   **File to Modify:** `topdata_package_release_builder/variant.py`
*   **Function to Modify:** `_rename_storefront_js_assets`
*   **Actions:**
    1.  Locate the `js_dist_dir` path variable.
    2.  Instead of constructing the `original_dir` path from the plugin name, scan the `js_dist_dir` for subdirectories.
    3.  Implement conditional logic:
        *   If exactly **one** subdirectory is found, treat it as the target asset directory to be renamed (`original_dir`).
        *   If **zero** or **more than one** subdirectory is found, log a warning stating that the asset directory could not be uniquely identified and skip the asset renaming process for that plugin.
    4.  Proceed with renaming this dynamically discovered directory and the primary `.js` file within it.

#### **Step 1.2: Enhance Global String Replacement**

The existing replacement logic only handles the `CamelCase` plugin name. This step will expand it to also replace the `kebab-case` version used in asset paths and HTML/Twig attributes.

*   **File to Modify:** `topdata_package_release_builder/variant.py`
*   **Function to Modify:** `_perform_global_replacement`
*   **Actions:**
    1.  At the beginning of the function, use the `string_utils.camel_to_kebab_for_js_asset` helper to generate the `kebab-case` versions of both the `original_name` and the `new_name`.
    2.  Within the file processing loop, after the existing replacement logic, add a new step to replace all occurrences of the original `kebab-case` string with the new `kebab-case` string.
    3.  This ensures that asset references in template files (`.twig`), JavaScript files (`.js`), and other configuration files are correctly updated.

---

### **Phase 2: Integration and Quality Assurance**

This phase ensures the new logic is correctly integrated and meets the project's quality standards.

#### **Step 2.1: Verify Integration within `transform_to_variant`**

Review the primary workflow function to ensure the enhanced helper functions are called correctly and the overall process remains coherent.

*   **File to Review:** `topdata_package_release_builder/variant.py`
*   **Function to Review:** `transform_to_variant`
*   **Actions:**
    1.  Confirm that the sequence of operations is logical: `composer.json` modification, main PHP file renaming, global replacement, and then JS asset renaming.
    2.  Ensure that no changes to function signatures in Phase 1 have broken the calls within this parent function.

#### **Step 2.2: Adhere to Coding Conventions**

Perform a final review of all code modifications to ensure they align with the project's established conventions.

*   **Reference Document:** `ai_docs/CONVENTIONS-PYTHON.md`
*   **Actions:**
    1.  Verify that all new and modified functions have mandatory type hints.
    2.  Ensure all code conforms to PEP8 and PEP257 standards.
    3.  Confirm that variable and function names use `snake_case`.

---

### **Summary of Modified Files**

Upon completion of this plan, the following file will have been modified:

*   `topdata_package_release_builder/variant.py`
