# Feature Specification: Main-Free Branch Publishing

**Feature Branch**: `n/a (no branch hook configured; feature dir 001-main-free-branch)`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Main-free branch publishing: on every build of an opted-in plugin, publish a renamed free variant including the injected Foundation code to a `main-free` git branch, so shop installations can update with a plain `git pull`."

## Clarifications

### Session 2026-11-06

- Q: Should the free branch publish only committed code or also uncommitted working-tree changes? → A: Committed code only; uncommitted changes abort the free publish, and the skip switch is the bypass.
- Q: Should the upload-disable switch also suppress the free-branch push? → A: No; it only affects file-server uploads, and the skip switch is the way to disable free work.
- Q: Should a build without code changes still create a snapshot commit because the release record timestamp changes? → A: No; the timestamp is ignored for change detection, so only content changes create a snapshot.
- Q: Should the free branch add a tag per snapshot (for example `free-v<version>`)? → A: No; snapshots are commits only, with the version in the commit message.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic free branch on every build (Priority: P1)

A developer maintains a paid Shopware plugin in a private repository. That repository carries
an opt-in manifest. On every build, the builder additionally produces the free variant and
publishes it to the `main-free` branch, so the developer's own shops can pull the update
without building the variant by hand.

**Why this priority**: This is the core value. Without the automatic branch update there is no
feature; the shop owner keeps doing manual variant builds.

**Independent Test**: Add the manifest to a plugin repository, run one build, clone the
`main-free` branch into a shop, and confirm the new version is present and obtainable with a
plain `git pull`.

**Acceptance Scenarios**:

1. **Given** a repository with an enabled manifest and no existing `main-free` branch,
   **When** a build completes, **Then** the remote `main-free` branch exists and contains the
   free variant of the built version.
2. **Given** a repository with an enabled manifest and an existing `main-free` branch,
   **When** a build completes, **Then** a new snapshot commit is appended and pushed.
3. **Given** a shop clone that is one build behind, **When** it runs `git pull`, **Then** it
   advances to the new snapshot without a reset or clean.
4. **Given** a repository without a manifest, **When** a build completes, **Then** no free
   branch, ZIP, sync, or notification is produced.

---

### User Story 2 - Self-contained, correctly renamed free variant (Priority: P2)

The published free variant must be installable on its own: it carries the renamed identity and
the foundation code it needs, so a shop does not need the separate foundation plugin.

**Why this priority**: A branch that does not install cleanly has no value, even if it updates
automatically.

**Independent Test**: Inspect the `main-free` tree of a plugin that depends on the foundation;
confirm the renamed identity, the injected foundation classes, and the absence of the
foundation dependency.

**Acceptance Scenarios**:

1. **Given** plugin `TopdataFooSW6`, **When** its free variant is published, **Then** the branch
   tree is named `FreeTopdataFooSW6` with matching namespace, main class, and asset paths.
2. **Given** the plugin requires the foundation package, **When** the free variant is published,
   **Then** the foundation classes are present, the requirement is removed, and the autoload
   mapping points at the free variant's foundation namespace.
3. **Given** the plugin does not require the foundation package, **When** the free variant is
   published, **Then** no foundation code is injected.

---

### User Story 3 - Optional free archive and notification (Priority: P3)

An operator may want a downloadable free package in addition to the branch. The archive and its
upload are off by default and enabled per repository, so a still-public file server is never
exposed unintentionally.

**Why this priority**: Convenience for manual installs and backups, but not required for the
core pull-based workflow.

**Independent Test**: With the archive flag off, confirm no free ZIP exists; turn it on and
confirm the ZIP is produced and follows the existing upload/notification path.

**Acceptance Scenarios**:

1. **Given** the archive flag is absent or false, **When** the free variant is published,
   **Then** no free ZIP is written, uploaded, or mentioned in notifications.
2. **Given** the archive flag is true, **When** the free variant is published, **Then** the ZIP
   is produced and handled like any other release archive.
3. **Given** the archive flag is true and uploads are disabled, **When** the build runs,
   **Then** the ZIP remains local and nothing is uploaded.

---

### User Story 4 - Safe failure and explicit skip (Priority: P4)

When publishing the free branch fails, the release must stop loudly instead of letting shops
pull a stale state. An explicit skip switch keeps an offline build possible.

**Why this priority**: Prevents silent staleness and data-loss-like surprises, but only matters
once the core flow works.

**Independent Test**: Force a publish failure and confirm a non-zero exit with no subsequent
upload or notification; then rerun with the skip switch and confirm the paid release proceeds.

**Acceptance Scenarios**:

1. **Given** an enabled manifest, **When** fetching, committing, or pushing the free branch
   fails, **Then** the build exits non-zero and skips manual publishing, uploads, and
   notifications.
2. **Given** the publish succeeds, **When** the build continues, **Then** the remaining release
   steps run as before.
3. **Given** the skip switch is passed, **When** the manifest is enabled, **Then** no free work
   happens, the paid release proceeds, and a warning is shown.

### Edge Cases

- The manifest file is present but not valid YAML, or `free` is not a mapping: abort with a
  clear error.
- The `free:` mapping is empty: enable with defaults.
- The configured branch name is empty, contains whitespace, `..`, or ref-invalid characters:
  abort.
- The `origin` remote is missing or the network is unreachable: abort.
- The remote repository is empty: the first push creates the branch and it may become the
  default branch there.
- The published branch moves while the build is running: the update is rejected and the build
  aborts; published history is never rewritten.
- A pre-existing branch with unrelated history: append to its remote tip, never rewrite.
- The working tree has uncommitted changes: the free publish aborts with a clear message, and
  the skip switch allows the paid release to proceed.
- Several builds run without a version bump or content change: no new snapshot commit is created,
  because the release record's timestamp is ignored for change detection.
- The archive flag is true while the file server is still public: the operator accepts the
  exposure; the default stays off.
- The upload-disable switch is used: the free branch is still published and only file-server
  operations are skipped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The builder MUST enable free-branch publishing only when the plugin repository
  contains a `.topdata/build.yaml` file with a mapping under the `free` key.
- **FR-002**: The builder MUST default the target branch to `main-free` and MUST honor
  `free.branch` when present.
- **FR-003**: The builder MUST derive the free variant with the fixed prefix `Free`, producing
  `Free<plugin-name>`.
- **FR-004**: The builder MUST rename the variant's plugin name, namespace, main class, and
  storefront asset paths consistently.
- **FR-005**: When the plugin declares a dependency on the foundation package, the builder MUST
  inject the foundation code into the free variant, rewrite its namespace to the free variant's
  namespace, remove the dependency, and register the new namespace for autoloading.
- **FR-006**: The free payload MUST use the same exclusions as the release ZIP plus `.topdata/`,
  MUST include the release record, and MUST NOT contain VCS metadata, build-tool state, tests,
  or development/AI files.
- **FR-007**: The free payload MUST place the plugin root at the branch root.
- **FR-008**: When the target branch is absent, the builder MUST create it with a single
  snapshot commit and no earlier history.
- **FR-009**: When the target branch exists, the builder MUST base the new snapshot commit on
  the branch's latest published state and append it.
- **FR-010**: The builder MUST publish the free branch on every build while the manifest is
  enabled, regardless of whether a version bump or tag occurred.
- **FR-011**: The builder MUST NOT rewrite published history; every update MUST extend the
  branch's latest published state so existing clones update without a reset.
- **FR-012**: The builder MUST compare the payload against the remote tip while ignoring the
  release record's creation timestamp, and MUST skip the commit and push when the remaining
  content is identical.
- **FR-013**: The snapshot commit message MUST include the build version.
- **FR-014**: The free variant's declared version MUST match the version of the same build.
- **FR-015**: Free-branch publication MUST complete before manual publishing, remote uploads,
  and notifications.
- **FR-016**: Any failure while preparing or publishing the free branch MUST abort the build
  with a non-zero exit and MUST prevent manual publishing, uploads, and notifications.
- **FR-017**: The builder MUST provide a skip switch that disables all free work even when the
  manifest is enabled, and MUST warn when it is used.
- **FR-018**: By default the free variant MUST NOT produce a ZIP, upload it, or reference it in
  notifications.
- **FR-019**: When `free.zip` is `true`, the builder MUST produce the free ZIP and apply the
  existing upload and notification behavior to it; an upload-disable switch MUST still suppress
  the upload while keeping the local ZIP.
- **FR-020**: An invalid manifest, an invalid branch name, a missing remote, or an unreachable
  remote MUST abort the build with a clear error.
- **FR-021**: While the working tree has uncommitted changes, the builder MUST NOT publish the
  free branch and MUST abort with an actionable message; the skip switch is the bypass.
- **FR-022**: The upload-disable switch MUST NOT suppress free-branch publication; it MUST only
  suppress file-server uploads, and only the skip switch may disable free work.
- **FR-023**: The builder MUST NOT create tags for free-branch snapshots; the version is recorded
  in the snapshot commit message and in the release record.

### Key Entities

- **Free manifest**: per-repository opt-in record under `.topdata/build.yaml`; holds the target
  branch and the optional archive flag.
- **Free variant**: the renamed, self-contained build of the plugin that is published to the
  free branch.
- **Free branch**: the long-lived append-only branch whose tip always reflects the last build's
  free variant.
- **Release record**: the build metadata file included in the free payload (version, source
  branch, commit, creation time).
- **Optional free archive**: the ZIP of the free variant, produced only when explicitly enabled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a repository with an enabled manifest, a single build results in a remote
  `main-free` branch containing the built version, and an existing shop clone reaches that
  version with one `git pull` and zero resets.
- **SC-002**: On a repository without a manifest, the paid build produces the same artifacts and
  side effects as before the feature (zero new branches, ZIPs, uploads, or notifications).
- **SC-003**: The published free tree contains zero excluded files (including `.topdata/`),
  zero foundation-package requirements, and the injected foundation classes.
- **SC-004**: In 100% of simulated publish failures, the build exits non-zero and performs zero
  uploads or notifications afterwards.
- **SC-005**: With the archive flag off, zero free ZIP artifacts exist on disk, on the file
  server, or in notifications.
- **SC-006**: A shop clone on the free branch can stay current across at least three consecutive
  builds using `git pull` only.
- **SC-007**: In 100% of runs with uncommitted changes, the free branch is left untouched and the
  user receives an actionable message or explicitly skips the free work.
- **SC-008**: With uploads disabled, the free branch still reaches the remote in 100% of builds,
  and no file-server transfer occurs.
- **SC-009**: Repeated builds with no content change add zero commits to the free branch.
- **SC-010**: Free-branch publication creates zero additional tags.

## Assumptions

- The manifest lives at `.topdata/build.yaml`; its absence means the feature is disabled.
- Only private or paid plugin repositories opt in; public plugins are already free in the store
  and carry no manifest.
- The free branch receives snapshot commits only, without an additional tag.
- The remote used for publishing is `origin`.
- The file server may still be public at rollout time, so the free archive defaults to off.
- Free publication requires a clean working tree; the paid build keeps its existing behavior for
  uncommitted changes.
- Change detection ignores the release record's creation timestamp, so builds without content
  changes do not create a snapshot.
- The existing variant transformation and foundation injection are reused; no new naming scheme
  is introduced.
- Publishing credentials come from the existing git configuration; no new secret handling is
  added.

## References

- Source design record: `specs/SPEC__261106-1__main-free-branch-publishing.md` (superseded by
  this specification)
