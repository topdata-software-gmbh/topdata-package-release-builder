# Checklist: Smarter Foundation Plugin Injection

## Phase 1: Implement Smart Foundation Path Resolution
- [ ] Create _get_foundation_path helper function in [`cli.py`](topdata_package_release_builder/cli.py)
- [ ] Implement path resolution logic (env var → default relative path)
- [ ] Add path validation with verbose logging
- [ ] Refactor build_plugin() to prepare for helper function

## Phase 2: Automatic Injection Based on composer.json
- [ ] Create has_foundation_dependency() in [`plugin.py`](topdata_package_release_builder/plugin.py)
- [ ] Implement composer.json dependency check
- [ ] Update build_plugin() injection logic in [`cli.py`](topdata_package_release_builder/cli.py)
- [ ] Implement forced injection with --with-foundation flag
- [ ] Add error handling for missing foundation plugin

## Phase 3: Final Touches and Documentation
- [ ] Update CLI help text for --with-foundation flag
- [ ] Add documentation to [`README.md`](README.md)
- [ ] Verify all test cases:
  - [ ] Standard case (with dependency, no flags)
  - [ ] Override case (with dependency, env var set)
  - [ ] No-op case (no dependency)
  - [ ] Force case (no dependency, --with-foundation)
  - [ ] Failure case (dependency found but path invalid)

## Verification
- [ ] Confirm all acceptance criteria are met