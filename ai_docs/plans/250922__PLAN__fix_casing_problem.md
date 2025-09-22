### Goal

The primary goal is to improve code organization and reusability by extracting all string case-conversion and text manipulation logic from `topdata_package_release_builder/variant.py` into a new, dedicated utility file named `topdata_package_release_builder/string_utils.py`. This refactoring will also incorporate the bug fix for the `camel_to_kebab` conversion for JavaScript assets.

---

### Phase 1: Create the String Utility Module

In this phase, you will create a new file to house the refactored functions.

1.  **Create a new file:**
    *   **File Path:** `topdata_package_release_builder/string_utils.py`

2.  **Populate the new file with the following content:**
    *   Add a docstring to explain the module's purpose.
    *   Add the necessary `re` import.
    *   Transfer and implement the different case-conversion and text-manipulation functions.

```python
# topdata_package_release_builder/string_utils.py
"""A collection of utility functions for string manipulation and case conversion."""

import re

def camel_to_kebab_for_composer(camel_str: str) -> str:
    """
    Convert a CamelCase string to kebab-case for composer.json package names.
    Example: 'FreeTopdataPlugin' -> 'free-topdata-plugin'
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', camel_str)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    return s2.lower()

def camel_to_kebab_for_js_asset(name: str) -> str:
    """
    Convert CamelCase to kebab-case, correctly handling acronyms and numbers for JS assets.
    Example: 'TopdataCategorySW6' -> 'topdata-category-s-w-6'
    """
    # Insert hyphen before uppercase letter followed by lowercase (e.g., Plugin -> -Plugin)
    name = re.sub(r'([A-Z])([a-z])', r'-\1\2', name)
    # Insert hyphen before uppercase letter preceded by a non-uppercase char (e.g., myPlugin -> my-Plugin)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', name)
    # Insert hyphen between letters and numbers (e.g., SW6 -> SW-6)
    name = re.sub(r'([A-Z])([0-9])', r'\1-\2', name)
    # Insert hyphen between consecutive uppercase letters (e.g., SW -> S-W)
    name = re.sub(r'([A-Z])([A-Z])', r'\1-\2', name)
    return name.lstrip('-').lower()

def prepend_variant_text(text: str, prefix: str, suffix: str) -> str:
    """
    Prepend prefix/suffix to text in a consistent format like '[PREFIX] [SUFFIX] Text'.
    It also removes any existing variant markers to prevent duplication.
    """
    variant_text = ""
    
    if prefix:
        variant_text += f"[{prefix.upper()}] "
    
    if suffix:
        variant_text += f"[{suffix.upper()}] "
    
    # Remove existing variant markers if they exist to avoid duplication
    text = re.sub(r'^(\[[A-Z]+\]\s*)+', '', text)
    
    return variant_text + text

```

---

### Phase 2: Refactor `variant.py` to Use the New Utility Module

Now, you will modify the existing `variant.py` file to remove the duplicated logic and use the new, centralized functions from `string_utils.py`.

1.  **Modify the file:** `topdata_package_release_builder/variant.py`

2.  **Add the import statement:**
    *   At the top of the file, with the other imports, add:
    ```python
    from . import string_utils
    ```

3.  **Refactor the `_modify_composer_json` function:**
    *   **Delete** the local helper functions `_camel_to_kebab` and `_prepend_variant_text` from within this function.
    *   **Find** this line:
        ```python
        kebab_name = _camel_to_kebab(new_name)
        ```
    *   **Replace** it with:
        ```python
        kebab_name = string_utils.camel_to_kebab_for_composer(new_name)
        ```
    *   **Find** all calls to `_prepend_variant_text` and **replace** them with `string_utils.prepend_variant_text`. There should be three instances.

4.  **Refactor the `_rename_storefront_js_assets` function:**
    *   **Delete** the local helper function `_camel_to_kebab` from within this function.
    *   **Find** these two lines:
        ```python
        original_kebab = _camel_to_kebab(original_name)
        new_kebab = _camel_to_kebab(new_name)
        ```
    *   **Replace** them with the corrected calls to the new utility module:
        ```python
        original_kebab = string_utils.camel_to_kebab_for_js_asset(original_name)
        new_kebab = string_utils.camel_to_kebab_for_js_asset(new_name)
        ```
    *   Also, add a more descriptive warning message when the original directory is not found, which will help in debugging. Find the `else` block for `if original_dir.exists():` and modify it like so:
        ```python
        else:
            console.print(f"[bold yellow]  Warning: Original JS directory not found. Looked for: {original_dir}[/bold yellow]")
            return # Exit if directory was not found
        ```
    *   Finally, ensure the file renaming logic correctly looks for the old filename inside the *newly renamed* directory.
        ```python
        # Rename JS file
        original_js_in_new_dir = new_dir / f"{original_kebab}.js"
        new_js = new_dir / f"{new_kebab}.js"

        if original_js_in_new_dir.exists():
            original_js_in_new_dir.rename(new_js)
            console.print(f"  Renamed JS file: {original_js_in_new_dir.name} -> {new_js.name}")
        else:
            console.print(f"[yellow]  Warning: JS file not found in new directory: {original_js_in_new_dir}[/]")
        ```

---

### Phase 3: Final Review

Please carefully review the changes to ensure:
1.  The new file `topdata_package_release_builder/string_utils.py` has been created correctly.
2.  The `variant.py` file now imports `string_utils`.
3.  All local helper functions (`_camel_to_kebab`, `_prepend_variant_text`) have been removed from `variant.py`.
4.  All calls to the old local functions have been correctly replaced with calls to the new functions in `string_utils`.
5.  The logic remains functionally identical, but is now properly modularized.

This plan will successfully refactor the code, improve maintainability, and fix the critical bug related to JavaScript asset renaming.



