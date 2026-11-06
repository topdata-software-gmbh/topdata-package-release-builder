---
filename: "/topdata/topdata-package-release-builder/_ai/backlog/reports/261106_1813__IMPLEMENTATION_REPORT__free-flag-cli-subcommand.md"
title: "Report: CLI subcommands to enable and disable the free flag"
createdAt: 2026-11-06 18:24
updatedAt: 2026-11-06 18:24
repoRoot: "/topdata/topdata-package-release-builder"
project: "topdata-package-release-builder"
status: completed
filesCreated: 5
filesModified: 7
filesDeleted: 0
tags: [cli, click, manifest, free-branch, config, dx]
documentType: IMPLEMENTATION_REPORT
planFile: "/topdata/topdata-package-release-builder/_ai/backlog/archive/261106_1813__IMPLEMENTATION_PLAN__free-flag-cli-subcommand.md"
specFile: "/topdata/topdata-package-release-builder/specs/001-main-free-branch/spec.md"
---

# Implementation Report: CLI subcommands for the free flag

## 1. Summary

Added `sw-build free enable|disable|status` to manage the `.topdata/build.yaml` free-branch
opt-in without hand-editing YAML. The manifest mutation layer writes atomically and preserves
unrelated keys, and the root Click entry point became a `DefaultGroup` so every legacy
`sw-build [options]` invocation still routes to the build command unchanged.

## 1.5 Prompt used

> `@~/.config/opencode/skills/implement-plan/SKILL.md`
> `@_ai/backlog/active/261106_1813__IMPLEMENTATION_PLAN__free-flag-cli-subcommand.md`

## 2. Files Changed

### Created

- `/topdata/topdata-package-release-builder/topdata_package_release_builder/commands/__init__.py:1` — command-group package marker.
- `/topdata/topdata-package-release-builder/topdata_package_release_builder/commands/free_cmd.py:1` — `free` group with `enable`, `disable`, `status`.
- `/topdata/topdata-package-release-builder/tests/test_free_manifest_mutation.py:1` — 13 mutation-layer tests.
- `/topdata/topdata-package-release-builder/tests/test_free_cli_commands.py:1` — 13 CLI and routing tests.
- `/topdata/topdata-package-release-builder/CHANGELOG.md:1` — Keep-a-Changelog `Unreleased` entry.

### Modified

- `/topdata/topdata-package-release-builder/topdata_package_release_builder/free_manifest.py:10` — added `os`/`tempfile` imports, `_read_document`, `_serialize_document`, `_write_document`, `enable_free`, `disable_free`.
- `/topdata/topdata-package-release-builder/topdata_package_release_builder/cli.py:31` — imports `free_group`; replaced `main()` with `DefaultGroup`, the root `cli` group, and `main()`.
- `/topdata/topdata-package-release-builder/README.md:66` — documents the manifest-management commands.
- `/topdata/topdata-package-release-builder/manual/30-configuration.de.md:44` — CLI subsection.
- `/topdata/topdata-package-release-builder/manual/30-configuration.en.md:44` — CLI subsection.
- `/topdata/topdata-package-release-builder/manual/40-usage.de.md:78` — "Free-Flag verwalten" subsection.
- `/topdata/topdata-package-release-builder/manual/40-usage.en.md:78` — "Managing the Free Flag" subsection.

### Deleted

None.

## 3. Key Changes

- `enable_free()` merges into an existing `free` mapping, only writes supplied `branch`/`zip`,
  validates the branch with `git check-ref-format`, and skips the write when the serialized
  document is unchanged (stable mtime, no noisy diff).
- `disable_free()` deletes the `free` key, and removes the manifest plus an empty `.topdata/`
  directory when nothing else remains.
- `_write_document()` writes a sibling temp file and uses `os.replace()` so a failed write
  cannot truncate a valid manifest.
- Invalid YAML or a non-mapping root aborts before any mutation; the CLI surfaces the parser
  message through `click.ClickException` (exit code 1).
- The new commands never build, commit, tag, push, upload or notify Slack.

## 4. Deviations from Plan

- **`DefaultGroup` implementation.** The plan's `resolve_command()` override cannot work:
  Click's group parser rejects unknown options (e.g. `--version-increment`) before
  `resolve_command` is reached. `DefaultGroup` now overrides `parse_args()` and prepends
  `build` when the first token is an option (except `-h`/`--help`). Verified against all
  routing-matrix forms; the observable behavior matches the plan.
- **Help output.** `sw-build --help` now shows the group help (listing `build` and `free`)
  rather than the build options, as the plan's routing matrix specifies. Build options are
  available via `sw-build build --help` and legacy invocations are unaffected.

## 5. Technical Decisions

- Reused `yaml.safe_load`/`safe_dump(sort_keys=False)` rather than a text-surgical editor, so
  comments are not preserved (accepted in plan Q3) but keys and forward-compatible unknown
  values survive.
- Idempotence is checked by comparing the canonical serialized document against the current
  file text, avoiding a rewrite when values are unchanged.
- Kept `build_plugin` as the existing `click.Command` and registered it explicitly as `build`,
  so `tests/test_free_cli.py` continues to invoke `cli.build_plugin` directly.

## 6. Testing Notes

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```

Result: `169 passed`, `ruff: All checks passed!` (baseline was 143 tests).

Manual smoke test performed in a throwaway directory: `free status` (disabled) → `free enable
--zip` → manifest contains `free:\n  zip: true` → `free status` (enabled) → `free disable`
→ `.topdata/` removed.

## 7. Usage Examples

```bash
sw-build free enable                    # writes .topdata/build.yaml with free: {}
sw-build free enable --branch main-free --zip
sw-build free disable                   # removes the free key
sw-build free status
sw-build --version-increment none       # legacy build invocation unchanged
```

## 8. Documentation Updates

- `README.md` gained an "Enable or disable the opt-in" command block in **Free Branch
  Publishing**.
- Both manual configuration files (`30-configuration.de.md`, `30-configuration.en.md`) gained
  a CLI snippet; both usage files (`40-usage.de.md`, `40-usage.en.md`) gained a dedicated
  manifest-management subsection.
- `CHANGELOG.md` was created with an `Unreleased / Added` entry.

## 9. Next Steps

- Optionally preserve YAML comments by switching to `ruamel.yaml` if maintainers care about
  in-file annotations.
- Add shell completion for the new `free` group if Click completion is set up in the future.
