# Implementation Plan: Main-Free Branch Publishing

**Branch**: `001-main-free-branch` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-main-free-branch/spec.md`

## Summary

Every build of an opted-in Shopware 6 plugin publishes a self-contained `Free<plugin-name>`
variant to an append-only `main-free` branch on `origin`, so shop installations can update with
a plain `git pull`. Opt-in is a committed `.topdata/build.yaml` manifest with a `free` mapping.
The free payload reuses the existing release copy, variant transformation, and foundation
injection, then publishes the resulting tree as a snapshot commit without touching the source
working tree or index. Free ZIP upload and notification reuse the existing release paths and
stay off unless the manifest enables them. Any publication failure aborts the build; an explicit
`--skip-free` switch is the only way to bypass free work.

## Technical Context

**Language/Version**: Python >=3.10 (declared floor in `pyproject.toml`; local test runtime 3.14)

**Primary Dependencies**: Existing `click`, `rich`, `pytz`, `python-dotenv`, `InquirerPy`,
`requests`; add `PyYAML>=6.0` for manifest parsing. External tools: `git` (required), `rsync`
(only when uploads are enabled, as today).

**Storage**: Filesystem only — existing release directory, temporary build directories, and the
source repository's git object database. No database or service state.

**Testing**: `pytest>=8` with `tmp_path` and real temporary git repositories for publication
tests; `ruff` with the existing `E9`, `F`, `B` rule selection. Run with
`uv run --extra dev pytest` and `uv run --extra dev ruff check .`.

**Target Platform**: Linux/macOS developer workstations and CI runners with a normal git CLI
(>=2.30 assumed; `git write-tree`/`commit-tree`/`push <sha>:<ref>` plumbing is long-stable).

**Project Type**: Single-project Python CLI (`sw-build` console script).

**Performance Goals**: No regression for repositories without a manifest. For opted-in
repositories, allow one additional plugin-tree copy (same cost class as the existing manual
variant build), one remote branch existence check/fetch, and one push per build.

**Constraints**:
- Publication is `origin`-only, append-only, fast-forward-only; never force-push and never rewrite
  published history or create tags.
- Free work requires a clean working tree; the source working tree and index must never be
  modified by publication.
- Free payload uses the release ZIP exclusions plus `.topdata/`; the plugin root is the branch
  root and `release_info.txt` is included.
- Manifest input is untrusted YAML; parse with a safe loader and validate all values.
- Python source must remain importable on 3.10 (PEP 604 unions already used in existing modules).
- Free-branch publication completes before manual publishing, uploads, and notifications.

**Scale/Scope**: One plugin repository per invocation; manifest under 1 KB; payload size is
bounded by the plugin tree (same as the existing release ZIP and variant builds).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The checked-in `.specify/memory/constitution.md` is the unfilled template: it defines no ratified
project principles, so there are no project-specific constitutional gates to enforce. The
repository's explicit conventions are therefore used as the gate:

- **Python floor**: keep `requires-python = ">=3.10"` source compatible.
- **Dependency discipline**: prefer reusing existing modules; add a parser dependency only where a
  hand-written parser would be riskier than a maintained library.
- **Test discipline**: new behavior ships with `pytest` coverage, including failure paths.
- **Lint discipline**: no new `E9`/`F`/`B` findings under the existing ruff configuration.
- **No new service surface**: this is a CLI feature; no API, database, or credential handling is
  introduced.

**Result**: PASS (no violations). Post-design re-check: PASS (see end of plan).

## Project Structure

### Documentation (this feature)

```text
specs/001-main-free-branch/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and alternatives
├── data-model.md        # Phase 1: manifest, payload, snapshot entities
├── quickstart.md        # Phase 1: end-to-end validation guide
├── contracts/           # Phase 1: manifest, CLI, git-branch, Python API contracts
│   ├── manifest.md
│   ├── cli.md
│   ├── git-branch.md
│   └── python-api.md
├── checklists/
│   └── requirements.md  # Existing spec-quality checklist
└── spec.md
```

### Source Code (repository root)

```text
topdata_package_release_builder/
├── cli.py                  # modified: --skip-free, ordering, free orchestration
├── free_manifest.py        # NEW: safe manifest parsing + validation
├── free_branch.py          # NEW: payload assembly, tree comparison, git publication
├── plugin.py               # modified: optional extra exclusions for the free payload
├── slack.py                # modified: optional free-archive block
├── variant.py              # reused unchanged: transform_to_variant(prefix="Free")
├── foundation_injector.py  # reused unchanged: inject_foundation_code(...)
├── release.py              # reused unchanged: create_release_info(...)
├── remote.py               # reused unchanged: sync_to_remote(...)
└── git.py                  # reused unchanged; free plumbing stays in free_branch.py

tests/
├── test_free_manifest.py   # NEW: parser/validation matrix
├── test_free_branch.py     # NEW: payload, comparison, git history/publication
└── test_free_cli.py        # NEW: ordering, abort, --skip-free, optional archive wiring
```

**Structure Decision**: Single-project layout, matching the existing flat
`topdata_package_release_builder/` module layout and `tests/` convention. Manifest parsing is
isolated from git publication so each can be tested without the other. Git plumbing lives in
`free_branch.py` rather than widening the existing `git.py`, because `git.py` is a collection of
simple working-directory helpers and must not gain a second, incompatible execution model.

## Implementation Outline

1. **Manifest loading**
   - Add `free_manifest.py` with a frozen `FreeManifest` dataclass (`enabled`, `branch`, `zip`,
     `path`) and `load_free_manifest(plugin_root)`.
   - Use `yaml.safe_load`; treat a missing file, `None` document, or missing `free` key as
     disabled; treat `free: null` / `free: {}` as enabled with defaults; reject a non-mapping root
     or non-mapping `free` value.
   - Validate `branch` (default `main-free`) with explicit checks plus
     `git check-ref-format refs/heads/<branch>`; validate `zip` is a boolean.

2. **Free payload**
   - Extend `copy_plugin_files` with an optional `extra_excludes` iterable, used by the free
     build to add `.topdata`.
   - Copy the plugin into a temp directory, run `transform_to_variant(..., prefix="Free",
     suffix="")`, then run `inject_foundation_code` when the build's existing injection decision
     is true, then write `release_info.txt` with `create_release_info(...)`.
   - Keep the existing source directory untouched.

3. **Append-only publication**
   - Implement pure-python helpers in `free_branch.py`:
     `build_free_payload(...)`, `publish_free_branch(...)`, and a result dataclass
     (`committed`, `branch`, `commit`, `version`, `payload_tree`, `previous_tip`).
   - Verify `origin` exists and the working tree is clean before any remote operation.
   - Detect the remote tip with `git ls-remote --heads origin refs/heads/<branch>`; distinguish an
     absent branch from an unreachable remote. Fetch only when the branch exists.
   - Write the payload as git objects with `git hash-object -w --no-filters` + `git mktree`
     (or an equivalent temporary index), then build the snapshot with `git commit-tree`.
     Use no parent for the first snapshot; use the fetched remote tip as parent afterwards.
   - Compare the payload against the remote tip before committing. Compare modes and blob IDs for
     every path; for `release_info.txt`, normalize away the `Created` row so a timestamp-only
     difference produces no commit. First snapshot always commits.
   - Push with `git push origin <commit>:refs/heads/<branch>` and no force flag. Treat a rejected
     push (remote moved) as a fatal error. Never create the branch locally or mutate the current
     checkout.
   - Commit message includes the built version (for example `Free release v1.4.0`).

4. **CLI orchestration**
   - Add `--skip-free`. Warn when the manifest is enabled and the switch is used.
   - Run the free step after the versioning workflow (so `composer.json`, commit, and tag are
     final and the tree can be checked clean) and before the paid ZIP, manual documentation
     publishing, remote uploads, and Slack notifications.
   - On any free error, let the existing top-level handler abort with a non-zero exit; do not
     continue to later release steps.
   - When `free.zip` is true, create the free ZIP with the existing `create_archive`, sync it when
     remote sync is enabled, and pass a free block to Slack. When false, create no archive and
     mention nothing about a free download.

5. **Notifications and summary**
   - Extend `send_release_notification` with an optional `free_info` argument rendered after the
     main package (and after the manual variant, when both exist).
   - Extend the success panel with the free branch name and, when enabled, the free archive path
     and download URL.

6. **Dependencies, docs, and tests**
   - Add `PyYAML>=6.0` to `pyproject.toml` and refresh `uv.lock`.
   - Document the manifest and `--skip-free` in `README.md`, `manual/30-configuration.*.md`, and
     `manual/40-usage.*.md` (keep the German/English pairs in sync).
   - Add unit tests for manifest parsing and validation.
   - Add integration tests using `tmp_path` git repositories (bare `origin` + working clone) for:
     first snapshot, append-only second snapshot, unchanged payload no-op, timestamp-only no-op,
     remote-move rejection with no force-push, missing/unreachable origin, dirty tree abort, and
     never touching the working tree/index.
   - Add CLI-level tests for `--skip-free`, ordering (free failure prevents upload/notification),
     optional free ZIP, and the no-manifest regression.

## Post-Design Constitution Check

- **Python floor**: new modules use `from __future__ import annotations` where needed and no
  syntax above 3.10. PASS.
- **Dependency discipline**: one parser dependency (`PyYAML`) replaces a fragile hand-rolled YAML
  reader; no other new dependency. PASS.
- **Test discipline**: every functional requirement maps to at least one unit or integration
  test in the outline. PASS.
- **Lint discipline**: the new modules are ordinary, typed-ish Python under the existing ruff
  selection. PASS.
- **No new service surface**: only CLI flags, a committed manifest file, and a git ref. PASS.

## Complexity Tracking

No constitutional or project-convention violations require justification.
