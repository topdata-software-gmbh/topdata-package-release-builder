# File Timestamp Verification Checklist

## Implementation Tasks

- [ ] **1. Implement verify_compiled_files function in plugin.py**
  - [ ] Create `verify_compiled_files` function with verbose and console parameters
  - [ ] Add logic to check if `dist/` directory exists
  - [ ] Implement file traversal for `.js` files in `dist/` directory
  - [ ] Add source file mapping (`.js` → `.ts` or `.js` → `.js`)
  - [ ] Implement timestamp comparison logic
  - [ ] Add detailed error reporting for outdated files
  - [ ] Handle edge cases (missing source files, etc.)

- [ ] **2. Integration of the function call in cli.py**
  - [ ] Import `verify_compiled_files` function in cli.py
  - [ ] Add verification call after git status check (around line 66-73)
  - [ ] Add status update message "Verifying compiled files..."
  - [ ] Implement error handling and graceful exit on failure
  - [ ] Ensure proper console output formatting

- [ ] **3. Testing scenarios**
  - [ ] **Test 1: Up-to-date files**
    - [ ] Create test scenario with compiled files newer than source
    - [ ] Verify build proceeds normally
    - [ ] Confirm no error messages displayed
  - [ ] **Test 2: Outdated files**
    - [ ] Create test scenario with source files newer than compiled
    - [ ] Verify error messages display correctly
    - [ ] Confirm build aborts with exit code 1
  - [ ] **Test 3: Missing dist directory**
    - [ ] Test behavior when `dist/` directory doesn't exist
    - [ ] Verify warning message is shown (if verbose)
    - [ ] Confirm build continues (as per plan)

- [ ] **4. Documentation updates**
  - [ ] Update README.md with new pre-build verification feature
  - [ ] Add section explaining the timestamp check behavior
  - [ ] Document error messages and troubleshooting steps
  - [ ] Update any relevant CLI help text
  - [ ] Add examples of successful and failed verification scenarios

## Verification Criteria

- [ ] All tests pass for the three scenarios above
- [ ] Error messages are clear and actionable
- [ ] Build process correctly aborts when files are outdated
- [ ] Documentation accurately reflects the new behavior
- [ ] Code follows existing project conventions and style

## Completion Notes

This checklist tracks the implementation of file timestamp verification to prevent packaging outdated compiled code. Each task should be completed and verified before moving to the next.