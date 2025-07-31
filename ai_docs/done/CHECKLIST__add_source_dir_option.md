# Checklist: Implementation of --source-dir Option

## Core Implementation
- [ ] Add `--source-dir` option to CLI command
- [ ] Modify `get_plugin_info()` to accept source_dir parameter
- [ ] Update `copy_plugin_files()` to use source_dir
- [ ] Pass source_dir through build_plugin workflow
- [ ] Implement git operations in source directory
- [ ] Add validation for source directory
- [ ] Update command documentation

## Testing
- [ ] Verify plugin builds from current directory by default
- [ ] Test with absolute path: `--source-dir=/path/to/plugin`
- [ ] Test with relative path: `--source-dir=../other-plugin`
- [ ] Verify error when source directory doesn't exist
- [ ] Verify error when composer.json is missing
- [ ] Test git operations in source directory
- [ ] Test with different plugin structures

## Documentation
- [ ] Update README.md with new option
- [ ] Add examples to CLI help text
- [ ] Document in ai_docs/PROJECT_SUMMARY.md

## Code Quality
- [ ] Ensure consistent path handling
- [ ] Add type hints for source_dir parameters
- [ ] Write unit tests for new functionality
- [ ] Update any affected test cases