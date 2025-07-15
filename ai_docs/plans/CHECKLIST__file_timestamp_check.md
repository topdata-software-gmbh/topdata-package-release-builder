# File Timestamp Verification Checklist

## Implementation Tasks

- [x] **1. Implement verify_compiled_files function in plugin.py**
  - [x] Create `get_newest_mtime` helper function
  - [ ] Use `source_dir` parameter for plugin root directory
  - [x] Implement type-based timestamp comparison logic
  - [x] Add error reporting for JS and CSS separately
  - [x] Handle edge cases (empty directories, missing files)

- [x] **2. Integration of the function call in cli.py**
  - [x] Import `verify_compiled_files` function in cli.py
  - [x] Add verification call after git status check, passing `source_dir`
  - [x] Add status update message "Verifying compiled files..."
  - [x] Implement error handling and graceful exit on failure

- [ ] **3. Testing scenarios**
  - [ ] **Test 1: Up-to-date files**
    - [ ] Verify build proceeds when compiled files are newer
  - [ ] **Test 2: Outdated JS files**
    - [ ] Verify error when JS source is newer than compiled JS
  - [ ] **Test 3: Outdated CSS files**
    - [ ] Verify error when CSS source is newer than compiled CSS
  - [ ] **Test 4: Mixed outdated files**
    - [ ] Verify error when both JS and CSS are outdated
  - [ ] **Test 5: Missing dist directory**
    - [ ] Verify warning and build continues
  - [ ] **Test 6: No source files**
    - [ ] Verify no errors when no source files exist
  - [ ] **Test 7: Directory resolution**
    - [ ] Verify paths resolve correctly to provided `source_dir`

- [ ] **4. Documentation updates**
  - [ ] Update README.md with new verification approach
  - [ ] Add section explaining type-based timestamp checks
  - [ ] Document error messages and troubleshooting

## Verification Criteria
- [ ] Errors clearly identify outdated file types and show full paths
- [ ] Build aborts only when source files are newer
- [ ] Handles cases with no source/compiled files
- [ ] Follows project conventions and style
- [ ] Uses correct plugin root directory (source_dir parameter)

## Completion Notes
This checklist tracks the implementation of type-based file timestamp verification using the plugin root directory to prevent packaging outdated compiled code.