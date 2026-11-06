---
description: "Task list for Main-Free Branch Publishing"
---

# Tasks: Main-Free Branch Publishing

**Input**: Design documents from `/specs/001-main-free-branch/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The implementation plan and quickstart require `pytest` coverage for new
behavior, including failure paths. Write each story's tests first and confirm they fail before
implementing.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified
independently. The feature is a single-project Python CLI; all paths are relative to the repository
root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: User story this task belongs to (US1, US2, US3, US4)
- Exact file paths are included in every task

## Path Conventions

- Package: `topdata_package_release_builder/`
- Tests: `tests/`
- Docs: `README.md`, `manual/`
- Specs: `specs/001-main-free-branch/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the only new runtime dependency and make it lockable.

- [x] T001 Add `PyYAML>=6.0` to the `dependencies` list in `pyproject.toml`, then refresh `uv.lock` with `uv lock` and confirm `yaml.safe_load` imports under `uv run python -c "import yaml"`

**Checkpoint**: Dependency available; no production code changed yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared manifest parsing, payload-copy support, and test fixtures required by all four
user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 [P] Create `topdata_package_release_builder/free_manifest.py` with frozen `FreeManifest(enabled, path, branch, zip)`, `FreeManifestError(ValueError)`, and `load_free_manifest(plugin_root)`; use `yaml.safe_load`, treat a missing file/`None` document/absent `free` key as disabled, treat `free: null`/`free: {}` as enabled with defaults, and abort on a non-mapping root or non-mapping `free`; validate `branch` (default `"main-free"`, reject non-string/empty/whitespace-padded/containing `..`, plus `git check-ref-format refs/heads/<branch>`) and `zip` (default `false`, reject non-boolean) per data-model.md's validation table
- [x] T003 [P] Add keyword-only `extra_excludes: Iterable[str] = ()` to `copy_plugin_files(...)` in `topdata_package_release_builder/plugin.py`, appending the patterns to `ignored_patterns` so default behavior is unchanged
- [x] T004 [P] Create shared pytest fixtures in `tests/conftest.py`: a bare `origin` repo, a working plugin clone with `composer.json` (`extra.shopware-plugin-class`, `version`), `src/<Plugin>.php`, a clean initial commit, and local `user.name`/`user.email`; plus a minimal foundation-plugin fixture for injection tests

**Checkpoint**: Manifest parsing, extra-exclusion support, and git fixtures exist and are importable.

---

## Phase 3: User Story 1 - Automatic free branch on every build (Priority: P1) 🎯 MVP

**Goal**: On every build of an opted-in plugin, publish the `Free<plugin-name>` payload as an
append-only snapshot commit on `origin/<branch>`, so shops update with a plain `git pull`.

**Independent Test**: Add `.topdata/build.yaml` with `free: {}`, run one build, clone
`main-free` into a shop checkout, and confirm the built version is present and one `git pull`
fast-forwards to it.

### Tests for User Story 1 (write first, must fail)

- [x] T005 [P] [US1] Add manifest-enablement tests in `tests/test_free_manifest.py`: absent file, empty/comments-only document, and missing `free` key produce disabled; `free: null` and `free: {}` produce `enabled=True`; default `branch == "main-free"` and `zip is False`
- [x] T006 [US1] Add first-publication integration tests in `tests/test_free_branch.py`: with no remote branch, `publish_free_branch` creates exactly one commit with no parent on `origin/main-free`, places `composer.json` at the branch root, includes `release_info.txt`, creates no local branch, and leaves the source working tree/index unchanged (`git status --porcelain` empty, current branch unchanged)
- [x] T007 [US1] Add append/pull integration tests in `tests/test_free_branch.py`: a second build appends exactly one commit whose single parent is the fetched tip; a shop clone fast-forwards with `git pull` only across two consecutive builds, with the version in the commit message
- [x] T008 [US1] Add idempotence tests in `tests/test_free_branch.py`: an unchanged payload, and a payload differing only in `release_info.txt`'s `Created` row, both return `committed=False` and `pushed=False` and add zero commits
- [x] T009 [US1] Add failure-path tests in `tests/test_free_branch.py`: missing `origin` and unreachable `origin` raise `FreePublishError` without creating history; a remote tip that moves between fetch and push makes the push fail without a force flag and without rewriting the remote history
- [x] T010 [P] [US1] Add a no-manifest regression test in `tests/test_free_cli.py`: without `.topdata/build.yaml`, a build creates no free branch, makes no free network call, adds no free ZIP or notification block, and leaves the paid release behavior unchanged

### Implementation for User Story 1

- [x] T011 [US1] Implement `build_free_payload(...)` in `topdata_package_release_builder/free_branch.py`: copy the source plugin with release exclusions plus `.topdata`, apply `transform_to_variant(prefix="Free", suffix="")`, write `release_info.txt` at the payload root with `create_release_info(...)`, and return `(free_name, payload_root)` without writing into `source_dir`
- [x] T012 [US1] Implement git plumbing and tree comparison in `topdata_package_release_builder/free_branch.py`: a `_run_git(repo_root, ...)` helper that never changes process CWD, `git remote get-url origin` validation, `git ls-remote --heads origin refs/heads/<branch>` branch detection, conditional fetch, `git hash-object -w --no-filters` + `git mktree` tree construction, and a comparator that checks path/mode/blob for every entry while normalizing away the `Created` row of `release_info.txt`
- [x] T013 [US1] Implement `publish_free_branch(...)` and frozen `FreeSnapshot` in `topdata_package_release_builder/free_branch.py`: require a clean working tree via `git status --porcelain`, build the tree, skip commit/push when identical, create an orphan snapshot with `git commit-tree` for a first publication or a single-parent snapshot on the fetched tip otherwise, and push with `git push origin <sha>:refs/heads/<branch>` (no `--force`, no tags, no local branch)
- [x] T014 [US1] Wire free publication into `topdata_package_release_builder/cli.py`: load the manifest after `handle_versioning_workflow` and before the paid ZIP/manual publishing/remote sync/Slack; when disabled, short-circuit with no free work or network call; on success report branch/commit or the unchanged-tree message and add the free branch name to `_show_success_message`

**Checkpoint**: With a manifest and no foundation requirement, US1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Self-contained, correctly renamed free variant (Priority: P2)

**Goal**: The published tree carries the `Free<plugin-name>` identity and, when the plugin requires
the foundation package, injected foundation code with the dependency removed and autoload updated.

**Independent Test**: Build a plugin that requires `topdata/topdata-foundation-sw6`; inspect the
`main-free` tree for the renamed identity, `src/Foundation/`, no foundation requirement, and the
`Topdata\Free<PluginName>\Foundation\` autoload entry. Build a non-foundation plugin and confirm no
injection.

### Tests for User Story 2 (write first, must fail)

- [x] T015 [US2] Add rename-identity integration tests in `tests/test_free_branch.py`: plugin `TopdataFooSW6` publishes `FreeTopdataFooSW6` with matching directory, namespace, main class, and storefront asset paths
- [x] T016 [US2] Add foundation-injection integration tests in `tests/test_free_branch.py`: `src/Foundation/` classes are present, `require` no longer lists `topdata/topdata-foundation-sw6`, `autoload.psr-4` contains `Topdata\Free<PluginName>\Foundation\`, and foundation namespaces are rewritten consistently
- [x] T017 [US2] Add a no-foundation integration test in `tests/test_free_branch.py`: when the plugin does not require the foundation, the payload has no `src/Foundation/` and no foundation autoload entry

### Implementation for User Story 2

- [x] T018 [US2] Extend `build_free_payload(...)` in `topdata_package_release_builder/free_branch.py` to run `inject_foundation_code(...)` after `transform_to_variant(...)` and only when `foundation_plugin_path is not None`, so injection sees the final `Free` identity
- [x] T019 [US2] Enforce payload invariants in `topdata_package_release_builder/free_branch.py`: the plugin root is the payload root (`composer.json` at root), `free_plugin_dir.name == Free<plugin_name>`, and the copy excludes `.topdata/`, VCS metadata, build-tool state, tests, and AI/dev files
- [x] T020 [US2] Pass the build's existing injection decision from `topdata_package_release_builder/cli.py` into `build_free_payload(...)`: reuse `should_inject`/`foundation_plugin_path` so `--with-foundation` and automatic dependency detection apply to the free variant identically

**Checkpoint**: US1 and US2 both work independently; the free variant installs as a standalone plugin.

---

## Phase 5: User Story 3 - Optional free archive and notification (Priority: P3)

**Goal**: Produce, upload, and announce a free ZIP only when the manifest's `free.zip` is `true`,
while `--no-sync` still keeps the archive local and never suppresses the branch.

**Independent Test**: With `free.zip` false, confirm no free ZIP exists and no free Slack block is
sent; with `free.zip` true, confirm the ZIP is created and follows the normal upload/notification
path; with `--no-sync`, confirm the ZIP stays local and the branch still publishes.

### Tests for User Story 3 (write first, must fail)

- [x] T021 [P] [US3] Add `free.zip` parsing/validation tests in `tests/test_free_manifest.py`: absent means `False`, `true` is accepted, and a non-boolean aborts with `FreeManifestError`
- [x] T022 [P] [US3] Add optional-archive CLI tests in `tests/test_free_cli.py`: `zip: false` writes no free ZIP, uploads nothing, and sends no free Slack block; `zip: true` creates `<FreeName>-v<version>.zip` and applies the existing upload/notification behavior; `zip: true` plus `--no-sync` keeps the ZIP local while the branch still publishes

### Implementation for User Story 3

- [x] T023 [US3] Create the optional free ZIP in `topdata_package_release_builder/cli.py` using the existing `create_archive(...)` only when `FreeManifest.zip` is true; produce no artifact and no mention when false
- [x] T024 [US3] Sync the optional free ZIP in `topdata_package_release_builder/cli.py` through `sync_to_remote(...)` with the same remote-config and `--no-sync` semantics as the paid archive, and assemble a `free_info` dict (`name`, `zip_name`, `zip_path`, `sync_status`, `download_url`, `zip_file_rsync_path`)
- [x] T025 [US3] Extend `send_release_notification(...)` in `topdata_package_release_builder/slack.py` with an optional `free_info: dict | None = None` block rendered after the main package and after the manual variant when both exist
- [x] T026 [US3] Extend `_show_success_message(...)` in `topdata_package_release_builder/cli.py` to show the free archive path and download URL only when `free.zip` produced one, in addition to the free branch name

**Checkpoint**: The optional archive workflow works without affecting the branch or default builds.

---

## Phase 6: User Story 4 - Safe failure and explicit skip (Priority: P4)

**Goal**: Any free-work failure aborts the build non-zero before manual publishing, uploads, or
notifications; `--skip-free` is the only bypass and prints a warning.

**Independent Test**: Force a publish failure and confirm non-zero exit with no subsequent upload
or notification; rerun with `--skip-free` and confirm the paid release proceeds with a warning.

### Tests for User Story 4 (write first, must fail)

- [x] T027 [P] [US4] Add the invalid-manifest matrix in `tests/test_free_manifest.py`: invalid YAML, non-mapping root, non-mapping `free`, `branch` that is non-string/empty/whitespace-padded/contains `..`/rejected by `git check-ref-format refs/heads/<branch>`, and non-boolean `zip` each abort with a clear `FreeManifestError`
- [x] T028 [P] [US4] Add abort/skip CLI tests in `tests/test_free_cli.py`: a dirty working tree, missing/unreachable `origin`, and a rejected push each exit non-zero and perform zero manual publishing, uploads, or Slack notifications; `--skip-free` with an enabled manifest prints a warning, performs no free work, and lets the paid release proceed; `--no-sync` still publishes the free branch

### Implementation for User Story 4

- [x] T029 [US4] Add `--skip-free` to the `build_plugin` command in `topdata_package_release_builder/cli.py` with help text matching `contracts/python-api.md`, and print a warning when the flag is used while the manifest is enabled
- [x] T030 [US4] Implement skip and abort behavior in `topdata_package_release_builder/cli.py`: when `--skip-free` is set, bypass all free work; let `FreeManifestError`/`FreePublishError` reach the existing top-level handler so the build exits non-zero before manual publishing, uploads, and notifications
- [x] T031 [US4] Verify and enforce switch independence in `topdata_package_release_builder/cli.py`: `--no-sync` must not suppress free-branch publication and only `--skip-free` may disable free work, with free publication ordered before paid uploads and notifications per `contracts/cli.md`

**Checkpoint**: All four stories are independently functional and failure paths are covered.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and full validation across all stories.

- [x] T032 [P] Document `.topdata/build.yaml` (`free.branch`, `free.zip`), `--skip-free`, the append-only/pull-safe behavior, and the clean-working-tree requirement in `README.md`
- [x] T033 [P] Add the manifest configuration section to `manual/30-configuration.de.md` and `manual/30-configuration.en.md`, keeping the pair in sync
- [x] T034 [P] Add the free-branch workflow and `--skip-free` usage to `manual/40-usage.de.md` and `manual/40-usage.en.md`, keeping the pair in sync
- [x] T035 Run `uv run --extra dev pytest` against `tests/` and `uv run --extra dev ruff check .` using `pyproject.toml` settings, then fix any failures so all tests pass with no new `E9`/`F`/`B` findings
- [x] T036 Execute the scenarios in `specs/001-main-free-branch/quickstart.md` (no-manifest regression, first publication, pull-safe append, no-op/timestamp-only, dirty tree and `--skip-free`, foundation injection, optional archive, failure paths, history invariants) against a throwaway bare origin and fix discrepancies

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately.
- **Foundational (Phase 2)**: Depends on Setup (PyYAML) — BLOCKS all user stories.
- **US1 (Phase 3)**: Depends on Foundational; delivers the MVP.
- **US2 (Phase 4)**: Depends on US1 because it extends `build_free_payload` and the CLI wiring.
- **US3 (Phase 5)**: Depends on US1 for the free workflow and manifest enablement.
- **US4 (Phase 6)**: Depends on US1 for publication and CLI wiring.
- **Polish (Phase 7)**: Depends on all desired stories being complete.

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational; no dependency on other stories.
- **US2 (P2)**: Extends the US1 payload builder; its own rename/injection tests are independent.
- **US3 (P3)**: Extends the US1 CLI flow; branch publication is verified independently of the archive.
- **US4 (P4)**: Wraps the US1 CLI flow with skip/abort behavior; independent failure tests.

### Within Each User Story

- Tests are written first and must fail before implementation.
- Manifest parsing (T002) before payload work (T011).
- Payload builder (T011) before git plumbing (T012) and publication (T013).
- Publication before CLI wiring (T014) so the CLI calls a tested function.
- US2 injection (T018) after the US1 transform-only builder (T011).
- US3 archive tasks after the US1 publication wiring (T014).
- US4 skip/abort after the US3 CLI additions so all free-work branches exist in one place.

### Parallel Opportunities

- Setup: T001 runs alone.
- Foundational: T002, T003, and T004 touch different files and can run together.
- US1: T005 (`test_free_manifest.py`) and T010 (`test_free_cli.py`) can run together; T006–T009 all edit `tests/test_free_branch.py` and must be sequential. Implementation T011–T013 all edit `free_branch.py` and must be sequential; T014 edits `cli.py`.
- US3: T021 (`test_free_manifest.py`) and T022 (`test_free_cli.py`) can run together. T023, T024, T026 all edit `cli.py` sequentially; T025 edits `slack.py`.
- US4: T027 (`test_free_manifest.py`) and T028 (`test_free_cli.py`) can run together.
- Polish: T032, T033, and T034 touch different files and can run together; T035 and T036 run after them.

---

## Parallel Example: User Story 1

```bash
# Different test files, safe to launch together:
Task: "Manifest-enablement tests in tests/test_free_manifest.py"
Task: "No-manifest regression test in tests/test_free_cli.py"

# Then sequential, because they share tests/test_free_branch.py:
Task: "First-publication integration tests in tests/test_free_branch.py"
Task: "Append/pull integration tests in tests/test_free_branch.py"
Task: "Idempotence tests in tests/test_free_branch.py"
Task: "Failure-path tests in tests/test_free_branch.py"
```

## Parallel Example: Foundational Phase

```bash
Task: "Create free_manifest.py with FreeManifest and load_free_manifest"
Task: "Add extra_excludes to copy_plugin_files in plugin.py"
Task: "Create shared git fixtures in tests/conftest.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (PyYAML).
2. Complete Phase 2: Foundational (manifest parser, extra exclusions, fixtures).
3. Complete Phase 3: US1 (payload, append-only publication, CLI wiring).
4. **STOP and VALIDATE**: run the US1 tests and quickstart scenarios 3–6; confirm a shop clone
   updates with one `git pull` and zero resets.
5. Deploy/demo if ready.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → test independently → MVP: automatic pull-safe free branch.
3. US2 → test independently → self-contained renamed/foundation-injected variant.
4. US3 → test independently → optional free ZIP, upload, and notification.
5. US4 → test independently → safe failure and `--skip-free`.
6. Polish → docs and full quickstart validation.

### Notes

- `[P]` marks different-file work; tasks sharing `cli.py`, `free_branch.py`,
  `tests/test_free_branch.py`, or a manual language pair are sequential.
- Every functional requirement FR-001..FR-023 is covered by at least one test or implementation
  task above; the coverage map is in `specs/001-main-free-branch/data-model.md` §6.
- No free-work task may add a tag, force-push, create a local free branch, or modify the source
  working tree/index.
- Commit after each task or logical group; do not commit unless the user asks.
