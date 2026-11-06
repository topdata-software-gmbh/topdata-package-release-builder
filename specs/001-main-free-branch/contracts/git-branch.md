# Contract: published free git branch

**Remote**: `origin` (the plugin repository's existing remote; no mirror or secondary remote).
**Ref**: `refs/heads/<free.branch>` (default `refs/heads/main-free`).

## History contract

- The branch is append-only.
- First publication (remote branch absent): one commit with **no parent** (orphan history),
  containing the complete free payload tree.
- Later publications: exactly one new commit whose single parent is the fetched remote tip.
- No merge commits, no tags, no force-push, no history rewrite.
- If the remote tip moves between fetch and push, the push is rejected and the build aborts.
  The builder MUST NOT retry with `--force`.
- A payload whose tree equals the remote tip (ignoring only `release_info.txt`'s `Created` value)
  produces no commit and no push.

## Tree contract

The commit tree root is the plugin root:

```text
composer.json
src/
  Free<PluginName>.php
  ...
release_info.txt
<other release files>
```

Required properties:

- `composer.json` is at the root (not nested under a plugin directory).
- No `.topdata/`, `.git*`, build-tool state, tests, AI/dev files, or node_modules.
- No `topdata/topdata-foundation-sw6` entry in `require` when injection occurred.
- `release_info.txt` is present and follows the existing machine-readable format.
- All paths and identities use the `Free<PluginName>` variant.

## Commit contract

- Commit message MUST include `v<version>` (for example `Free release v1.4.0`).
- The commit is created with the repository's configured git author/committer.
- The commit is pushed by SHA to the branch ref:
  `git push origin <sha>:refs/heads/<branch>`.
- The local source checkout is not switched, and no local branch named `<free.branch>` is created.

## Fetch contract

- Verify `origin` exists before any network operation.
- Check branch existence with `git ls-remote --heads origin refs/heads/<branch>`.
- Empty result: treat as a first publication.
- Non-zero result: abort (remote unreachable/refused); do not create a fresh orphan history.
- When the branch exists, fetch it and use the fetched tip as the parent.

## Consumer contract (shop clone)

A clone with `main-free` checked out and no local changes MUST be able to update with:

```bash
git pull
```

with no `reset`, `clean`, or manual conflict resolution for a normal fast-forward update.

## Idempotence contract

Repeated builds with no content change (including only a new `Created` timestamp) MUST add zero
commits and push nothing. A version change, source change, transformed identity change, or
provenance change (branch/commit in `release_info.txt`) MUST add one commit.
