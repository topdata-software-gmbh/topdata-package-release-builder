---
filename: "specs/SPEC__261106-1__main-free-branch-publishing.md"
title: "Main-Free Branch Publishing"
specId: 261106-1
status: Superseded
date: 2026-11-06
createdAt: 2026-11-06 15:15
updatedAt: 2026-11-06 15:22
priority: medium
estimatedComplexity: moderate
tags: [git, release, variant, shopware, workflow]
documentType: SPEC
---

# Main-Free Branch Publishing

## Objective
Every build of an opted-in Topdata Shopware 6 plugin publishes a renamed `Free` variant to a
`main-free` git branch. Shop installations clone that branch and update with a plain
`git pull`, without building the variant manually or relying on a ZIP archive.

## Scope
- Per-repository opt-in through a `.topdata/build.yaml` manifest with a `free` mapping.
- Fixed variant prefix `Free`, derived with the existing variant transformation.
- Foundation injection for the free variant, making it self-contained.
- Publication to an orphan `main-free` branch on every build, append-only and fast-forward only.
- Free payload uses the same exclusions as the ZIP, plus `.topdata/`.
- Optional Free ZIP, remote sync, and Slack notification via `free.zip`.
- Hard release abort when publication fails, with `--skip-free` as an escape hatch.
- Publication occurs before manual publishing, remote sync, and Slack notification.

## Non-goals
- Changing the paid build, its version bump, tag, ZIP, or remote layout.
- Publishing a free branch for public plugins; those are already free in the store and carry no
  manifest.
- Separate mirror repositories or non-`origin` remotes.
- Force-pushing or rewriting the free branch history.
- Tagging the free branch (commits only, unless an open question resolves otherwise).
- Merging the free branch back into `main`.
- Creating or editing `.topdata/build.yaml` automatically.

## Requirements

### Requirement: Opt-in Manifest
The builder SHALL enable free-branch publishing only when the plugin repository contains a
`.topdata/build.yaml` file with a mapping under the `free` key.

#### Scenario: Manifest enables the feature
- **WHEN** `.topdata/build.yaml` contains a `free` mapping
- **THEN** the free variant is built and published as part of the build
- **AND** the branch defaults to `main-free`

#### Scenario: Custom branch name
- **WHEN** the `free` mapping sets `branch: my-free`
- **THEN** the builder publishes to `my-free`

#### Scenario: No manifest, or no free key
- **WHEN** the file is absent or has no `free` key
- **THEN** the paid build behaves exactly as before
- **AND** no free build, branch, worktree, ZIP, sync, or Slack work is performed

#### Scenario: Invalid manifest
- **WHEN** the file is not valid YAML or `free` is not a mapping
- **THEN** the build aborts with a clear error and a non-zero exit

### Requirement: Free Variant Identity
The builder SHALL derive the free variant with the existing variant transformation and the fixed
prefix `Free`, yielding `Free<plugin-name>` in name, namespace, class, and asset paths.

#### Scenario: Rename of a plugin
- **WHEN** the plugin is `TopdataFooSW6`
- **THEN** the free variant is `FreeTopdataFooSW6`
- **AND** its namespace, main class, and storefront asset paths are renamed consistently

#### Scenario: Version consistency
- **WHEN** the paid build bumps the version
- **THEN** the free variant's `composer.json` carries the same version

### Requirement: Self-Contained Foundation
When the plugin declares `topdata/topdata-foundation-sw6`, the free variant SHALL include the
injected foundation code with namespaces rewritten to the free variant's namespace and the
dependency removed from `require`.

#### Scenario: Foundation dependency present
- **WHEN** the plugin's `composer.json` requires the foundation package
- **THEN** the free payload contains `src/Foundation/` classes
- **AND** `require` no longer lists `topdata/topdata-foundation-sw6`
- **AND** `autoload.psr-4` registers the free variant's Foundation namespace

#### Scenario: Foundation plugin unavailable
- **WHEN** injection is required but the foundation plugin cannot be located
- **THEN** the build aborts with a clear error and a non-zero exit

### Requirement: Release Payload Content
The free branch tree SHALL equal the release payload: same exclusions as the ZIP plus
`.topdata/`, including `release_info.txt`, with the plugin root at the branch root.

#### Scenario: Excluded files
- **WHEN** the free payload is published
- **THEN** it contains no `.topdata/`, `.git*`, build-tool state, tests, or AI/dev files
- **AND** `composer.json` is at the branch root

#### Scenario: Provenance
- **WHEN** the free payload is published
- **THEN** it contains `release_info.txt` for the build

### Requirement: Branch Publication
The builder SHALL publish the free variant to the configured branch on every build when enabled.

#### Scenario: Branch does not exist
- **WHEN** the target branch is absent on the remote
- **THEN** the builder creates it as an orphan branch with one snapshot commit
- **AND** the push creates the branch on the remote

#### Scenario: Branch exists
- **WHEN** the target branch exists on the remote
- **THEN** the builder fetches the remote tip and appends a new snapshot commit on top of it
- **AND** the commit message includes the build version

#### Scenario: Identical payload
- **WHEN** the computed payload tree is byte-identical to the remote tip tree
- **THEN** no commit is created and no push is performed
- **AND** the build still succeeds

### Requirement: Pull-Safe History
The builder SHALL never force-push the free branch; every update SHALL fast-forward from the
previous remote tip so existing clones update with `git pull` alone.

#### Scenario: Existing shop clone updates
- **WHEN** a shop clone on `main-free` is one build behind
- **THEN** `git pull` fast-forwards to the new snapshot
- **AND** no reset or clean is required

#### Scenario: Remote move detected
- **WHEN** the remote branch moved between fetch and push and the push is rejected
- **THEN** the build aborts with a clear error
- **AND** the builder does not force-push

### Requirement: Build Ordering and Failure
Free-branch publication SHALL complete before manual publishing, remote synchronization, and
Slack notification; any failure SHALL abort the release with a non-zero exit.

#### Scenario: Publication fails
- **WHEN** fetching, committing, or pushing the free branch fails
- **THEN** the build exits non-zero
- **AND** manual publishing, remote sync, and Slack notification are not executed

#### Scenario: Publication succeeds
- **WHEN** the free branch is published
- **THEN** the remaining release steps continue as before

### Requirement: Optional Free Archive
By default the free variant SHALL NOT produce a ZIP, sync it, or reference it in Slack. When
`free.zip` is `true`, the builder SHALL produce the Free ZIP and run the existing remote-sync and
Slack behavior for it.

#### Scenario: Default behavior
- **WHEN** `free.zip` is absent or `false`
- **THEN** no Free ZIP is written to the release directory
- **AND** nothing is synced or mentioned in Slack for the free variant

#### Scenario: Archive enabled
- **WHEN** `free.zip` is `true`
- **THEN** the Free ZIP is written and synced, and Slack references it
- **AND** `--no-sync` still suppresses the upload while keeping the local ZIP

### Requirement: Skip Switch
`--skip-free` SHALL disable all free-build work even when the manifest enables it.

#### Scenario: Skip requested
- **WHEN** `--skip-free` is passed and the manifest is enabled
- **THEN** no free variant is built, no branch is touched, and no Free ZIP is created
- **AND** the paid release proceeds and a warning is logged

## Edge Cases
- An empty `free:` mapping enables the feature with all defaults.
- An invalid branch name (empty, whitespace, `..`, or ref-invalid characters) aborts the build.
- A missing `origin` remote or unreachable network aborts the build.
- Pushing into an empty remote repository creates the branch; it may become that repository's
  default branch.
- Uncommitted working-tree changes are included, matching the existing copy semantics.
- Multiple builds without a version bump produce multiple branch commits because
  `release_info.txt` records a new creation timestamp.
- A pre-existing `main-free` branch with unrelated history is not rewritten; the new snapshot is
  appended to its remote tip.

## Success Criteria
- On a repository with an enabled manifest, one `sw-build` run creates or updates
  `origin/main-free` so a clone on that branch obtains the new version with `git pull` alone.
- Without a manifest, the paid build output and side effects are unchanged.
- The free tree contains no `.topdata/` or dev files, lists no foundation dependency, and
  contains the injected Foundation classes.
- A publication failure yields a non-zero exit and no remote sync or Slack notification.
- With `free.zip: false`, no Free ZIP exists on disk, on the file server, or in Slack.
- Automated tests cover manifest parsing, variant identity, foundation injection, orphan branch
  creation, append-only commits, no-force-push behavior, failure aborts, and `--skip-free`.

## Open Questions
- [NEEDS CLARIFICATION: Should the manifest be `.topdata/build.yaml` (assumed) or a dedicated
  `.topdata/free.yaml`?]
- [NEEDS CLARIFICATION: Should the free branch receive a tag such as `free-v<version>` in
  addition to the snapshot commit, or commits only?]

## References
- **Superseded by**: `specs/001-main-free-branch/spec.md` (project-standard specification).
- `topdata_package_release_builder/cli.py:288` — existing remote-sync step and ordering.
- `topdata_package_release_builder/cli.py:295` — existing `--variant-*` build path reused here.
- `topdata_package_release_builder/variant.py:16` — `transform_to_variant` rename logic.
- `topdata_package_release_builder/foundation_injector.py:172` — `inject_foundation_code`.
- `topdata_package_release_builder/plugin.py:44` — `copy_plugin_files` exclusion list.
- `topdata_package_release_builder/git.py:80` — existing branch/tag push helpers.
- `topdata_package_release_builder/workflow.py:14` — version bump, commit, and tag flow.
- `pyproject.toml` — dependency set; YAML parsing needs a parser.
