# Phase 0 Research: Main-Free Branch Publishing

All unknowns from the Technical Context are resolved here. No item remains NEEDS CLARIFICATION.

## 1. How should `.topdata/build.yaml` be parsed?

**Decision**: Add `PyYAML>=6.0` and parse with `yaml.safe_load`. Validate the document shape
explicitly: a missing file, an empty document, or a missing `free` key disables the feature;
`free: null` and `free: {}` enable it with defaults; a non-mapping root or a non-mapping `free`
value aborts with a clear error.

**Rationale**: YAML is the format named by the spec. `safe_load` is the standard, non-executing
loader. The manifest is small but untrusted input; a hand-written parser would have to reproduce
quoting, comments, booleans (`true`/`yes`), nesting, and error reporting, which is more risk than
a one-purpose dependency. PyYAML is already present in the environment/transitive set, so the
incremental install cost is low; it still must be declared explicitly in `pyproject.toml`.

**Alternatives considered**:
- Hand-written line parser: rejected — silently accepting invalid YAML violates FR-020 and the
  invalid-manifest edge case.
- JSON or TOML manifest: rejected — the spec and source record fix the path/format as
  `.topdata/build.yaml`.
- `yaml.full_load`: rejected — unnecessary object construction is an avoidable risk for a config
  file.

## 2. How should the free branch be published without disturbing the checkout?

**Decision**: Use git plumbing against the source repository: write payload blobs with
`git hash-object -w --no-filters`, assemble trees with `git mktree`, create the commit with
`git commit-tree` (parent = fetched remote tip, or no parent for the first snapshot), and push the
commit SHA directly with `git push origin <sha>:refs/heads/<branch>`.

**Rationale**: The source checkout must keep its current branch, index, and working tree. A
plumbing-based writer never checks out the free branch, never creates a local branch, never
touches the index, and therefore cannot leave the user on the wrong branch or with staged
changes. It also makes append-only behavior explicit: the parent is exactly the fetched remote
tip, and the push is a normal fast-forward push with no force flag. If the remote moved after the
fetch, git rejects the push, which is the required behavior (FR-011, remote-move edge case).
`--no-filters` prevents line-ending/attribute conversion from changing payload bytes.

**Alternatives considered**:
- Temporary clone of `origin`, commit, push: rejected — extra network clone and credential
  surface per build; slower and unnecessary because the source repo already has the object
  database.
- `git worktree add` in a temp directory: rejected — writes linked-worktree metadata under
  `.git/worktrees`, can leave stale entries after a crash, and makes "never touch the checkout"
  harder to guarantee. It also needs branch/index management the plumbing approach avoids.
- `git fast-import`: rejected — more machinery than needed for one snapshot; harder to test and
  debug.
- Force-push the new tree: rejected — violates pull-safety (FR-011) and the non-goal of rewriting
  history.

## 3. How is the payload compared against the remote tip?

**Decision**: Compare the complete payload tree with the remote tip tree by path, file mode, and
blob ID. For `release_info.txt` only, compare content after removing/normalizing the `Created`
row. If every other entry matches, skip commit and push; otherwise create a snapshot.

**Rationale**: FR-012 says the creation timestamp is the only field to ignore. Excluding all of
`release_info.txt` would miss version, branch, or commit-provenance changes, which are real
content changes. Comparing blob IDs (computed locally with `git hash-object`) avoids a checkout of
the remote tree, and comparing modes catches executable-bit changes. The remote file can be read
with `git cat-file -p <tip>:release_info.txt` for the normalized timestamp comparison.

**Alternatives considered**:
- Compare only `release_info.txt` content: rejected — tree changes elsewhere would be missed.
- Exclude `release_info.txt` from change detection entirely: rejected — a version-only change
  would not create a snapshot, violating FR-013/FR-014.
- Compare a recursive directory hash generated outside git: rejected — duplicate hashing logic and
  a second source of truth versus git's own tree comparison.

## 4. How is branch existence distinguished from an unreachable remote?

**Decision**: Run `git remote get-url origin` first (missing remote aborts), then
`git ls-remote --heads origin refs/heads/<branch>`. Empty output means the branch is absent;
a non-zero exit means the remote is unreachable or refused and aborts. Fetch the branch only when
it exists.

**Rationale**: `git fetch origin <missing-branch>` also exits non-zero, so it cannot distinguish
"branch not created yet" (a supported first-build case) from "network/auth failure" (a required
abort). `ls-remote` gives a clean empty-vs-error split. The extra round trip is small and only on
opted-in builds.

**Alternatives considered**:
- Treat any `fetch` failure as "branch absent": rejected — a network outage would silently create
  a fresh orphan history instead of aborting, violating FR-020 and the append-only guarantee.
- `git ls-remote --exit-code`: rejected as the primary check because its exit code conflates "no
  matching ref" with command failure unless parsed carefully; an explicit empty-output check is
  clearer.

## 5. How is "committed code only" enforced?

**Decision**: After the versioning workflow and before any free work, run
`git status --porcelain` in the plugin repository. Any output aborts the free publication with an
actionable message; `--skip-free` is the documented bypass.

**Rationale**: The clarification requires committed code only and says uncommitted changes abort
the free publish. Checking after versioning is important: a `patch`/`minor`/`major` bump creates a
commit and tag first, so the tree becomes clean; `none` leaves any pre-existing changes in place.
The check is intentionally broader than "modified tracked files" — staged and untracked files are
also uncommitted and would otherwise leak into the payload.

**Alternatives considered**:
- Publish from `HEAD` with `git archive`: rejected — would drop ignored-but-required compiled
  assets and would not match the existing release copy semantics.
- Warn and continue: rejected — the clarification explicitly requires abort, with the skip switch
  as the only bypass.

## 6. What is the correct order of variant transformation and foundation injection?

**Decision**: Copy → transform to the `Free` variant → inject foundation code → write
`release_info.txt`.

**Rationale**: `transform_to_variant` rewrites the plugin class, namespaces, and asset paths.
`inject_foundation_code` derives the target namespace from the (already transformed) composer
`shopware-plugin-class` and rewrites the foundation namespace into
`Topdata\Free<Name>\Foundation`. Transforming first means injection has the final identity and
does not need a second namespace pass. It also removes the foundation dependency from the
transformed composer file. This composes the two existing, separately tested operations without
changing either.

**Alternatives considered**:
- Inject first, then transform: workable in most cases because the global replacement would also
  rewrite the injected namespace, but it relies on incidental replacement order and makes the
  final autoload map harder to reason about.
- Build a separate free-specific variant implementation: rejected — duplicates existing rename and
  injection logic and risks divergence from paid/variant output.

## 7. How should the optional free archive and notification work?

**Decision**: Reuse `create_archive`, `sync_to_remote`, and the existing no-sync/remote-config
semantics. Add an optional `free_info` block to `send_release_notification` and to the success
panel. The free ZIP is created only when `free.zip` is true; it is uploaded only when remote sync
is configured and `--no-sync` is absent.

**Rationale**: The spec asks for "existing upload and notification behavior" on the free archive,
not a second release pipeline. Extension by one optional block preserves current behavior for
releases without a free archive, and keeps `--no-sync` semantics identical to the paid ZIP.

**Alternatives considered**:
- Treat the free archive as another `variant_info`: rejected — a build can already have a manual
  `--variant-*` variant; overloading the same field would mix two different artifacts and confuse
  the Slack header.
- Send a separate Slack message for the free archive: rejected — duplicates the release
  notification and risks partial notification ordering.

## 8. Where does the free step belong in the CLI?

**Decision**: After `handle_versioning_workflow` returns and before the paid copy/ZIP, manual
documentation publishing, remote sync, and Slack notification.

**Rationale**: Versioning is the last source-tree mutation; running after it gives the free step
a stable version and a chance at a clean tree. Running before the paid artifact steps satisfies
FR-015 and FR-016: a free failure cannot leave manual publishing, uploads, or notifications
already performed. Building the free payload in its own temp directory means the paid build is
unaffected by success or failure.

**Alternatives considered**:
- After the paid ZIP but before sync: still satisfies the letter of the ordering, but performs
  paid work that a free failure throws away and makes the failure path noisier.
- After all uploads: violates FR-015/FR-016.

## 9. How is the new code split across modules?

**Decision**: Two new modules:
- `free_manifest.py`: manifest dataclass, safe parsing, branch/zip validation, no git side
  effects beyond `git check-ref-format`.
- `free_branch.py`: payload assembly, git plumbing, tree comparison, publication result.

Existing modules gain only narrow changes: `plugin.py` optional `extra_excludes`, `slack.py`
optional `free_info`, `cli.py` orchestration and `--skip-free`.

**Rationale**: Parsing and publication fail for different reasons and are easiest to test
separately. Keeping git plumbing out of `git.py` avoids mixing the existing chdir-based helpers
with subprocess calls that must run against an explicit repository and must never change the
process working directory. A single `free_branch.py` is still small enough to stay cohesive.

**Alternatives considered**:
- One large `free.py`: rejected — harder to test parsing without git fixtures and vice versa.
- Extend `git.py` with plumbing: rejected — the module's current contract is "chdir and run a
  simple command"; a second execution model in the same file invites accidental use of the wrong
  helper.

## 10. What does the test strategy look like?

**Decision**:
- Pure unit tests for manifest parsing/validation and payload naming.
- Integration tests with real temporary git repositories: a bare `origin`, a working plugin
  clone, and `git` configured with local `user.name`/`user.email`. Verify commit parentage,
  tree layout, no force-push, no local branch creation, and unchanged working tree/index.
- CLI tests via `click.testing.CliRunner` with mocked upload/notification boundaries to prove
  ordering and abort behavior.

**Rationale**: The risk concentrates in git history shape and failure ordering, neither of which
a pure unit test can prove. Real repositories are fast and dependency-free (git is already
required by the tool). Mocking only the network/rsync/Slack boundaries keeps tests hermetic.

**Alternatives considered**:
- Mock all git calls: rejected — would assert the implementation's arguments rather than the
  resulting history, missing the append-only and no-force-push guarantees.
- Test only against a remote service: rejected — not hermetic and not needed; local bare repos
  exercise the same push semantics.

## Open Items

None. All Technical Context unknowns are resolved by the decisions above.
