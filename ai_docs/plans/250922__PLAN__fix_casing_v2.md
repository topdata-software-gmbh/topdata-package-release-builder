# Implementation Plan: Fix JS Asset Renaming in Variant Creation

This plan outlines the steps to fix a bug in the `camel_to_kebab_for_js_asset` function, which causes incorrect path generation for JavaScript assets during plugin variant creation. The fix will be validated by newly created unit tests.

## Phase 1: Test Environment Setup

**Goal:** Prepare the project for unit testing by adding a test runner and creating the necessary file structure.

1.  **Update `pyproject.toml`:**
    *   Add `pytest` to the project's development dependencies. This allows for running the tests.
    *   Create a new `[project.optional-dependencies]` section for `test` if it doesn't exist.

2.  **Create Test Directory and Files:**
    *   Create a `tests/` directory in the project root for all test files.
    *   Create an empty `tests/__init__.py` file to ensure the directory is treated as a Python package.
    *   Create the test file `tests/test_string_utils.py` which will contain the unit tests for the case conversion logic.

## Phase 2: Unit Test Implementation (TDD)

**Goal:** Create specific unit tests that replicate the bug and verify the correct behavior of the `camel_to_kebab_for_js_asset` function.

1.  **Populate `tests/test_string_utils.py`:**
    *   Import the `pytest` library and the `camel_to_kebab_for_js_asset` function.
    *   Create a parameterized test function using `@pytest.mark.parametrize` to cover multiple scenarios efficiently.
    *   **Include a test case that specifically reproduces the bug:**
        *   Input: `'TopdataCategoryFilterSW6'`
        *   Expected Output: `'topdata-category-filter-s-w6'`
    *   **Add other test cases to prevent regressions and cover edge cases:**
        *   Simple camel case: `('MyPlugin', 'my-plugin')`
        *   Acronyms: `('MySWPlugin', 'my-s-w-plugin')`
        *   Acronym at the end: `('AnotherSW', 'another-s-w')`
        *   Numbers not part of an acronym: `('Plugin2Go', 'plugin2-go')`

2.  **Run Tests and Confirm Failure:**
    *   Execute `pytest` from the command line.
    *   Verify that the test run fails, specifically on the `TopdataCategoryFilterSW6` case. This confirms the bug is successfully reproduced by the test suite.

## Phase 3: Bug Fix Implementation

**Goal:** Correct the flawed logic in the `camel_to_kebab_for_js_asset` function.

1.  **Navigate to the Target File:**
    *   Open `topdata_package_release_builder/string_utils.py`.

2.  **Modify the Regular Expression:**
    *   Locate the `camel_to_kebab_for_js_asset` function.
    *   Find the line with the regular expression substitution that handles consecutive uppercase letters.
    *   **Change this line:**
        ```python
        # FROM:
        name = re.sub(r'([A-Z])([A-Z])(?![0-9])', r'\1-\2', name)

        # TO:
        name = re.sub(r'([A-Z])([A-Z])', r'\1-\2', name)
        ```
    *   This change removes the negative lookahead `(?![0-9])` that was incorrectly preventing the split between `S` and `W` in `SW6`.

3.  **Update the Code Comment:**
    *   The comment associated with the modified line is now incorrect.
    *   **Change the comment:**
        ```python
        # FROM:
        # This correctly handles 'SW' -> 'S-W' but leaves 'W6' untouched.
        
        # TO:
        # This correctly handles 'SW' -> 'S-W' and 'W6' -> 'W6' (as it's handled by the previous regex).
        ```

## Phase 4: Verification and Cleanup

**Goal:** Confirm the bug is fixed, ensure no new issues have been introduced, and clean up the project configuration.

1.  **Run Tests and Confirm Success:**
    *   Execute `pytest` from the command line again.
    *   Verify that all tests, including the one that previously failed, now pass. This confirms the fix is effective and has not caused any regressions.

2.  **Revert `pyproject.toml` Changes:**
    *   To keep the production dependencies clean, remove the `pytest` dependency and the `[project.optional-dependencies]` section that was added in Phase 1. The test files will remain in the repository for future development but won't be part of the package's installation dependencies.

---

