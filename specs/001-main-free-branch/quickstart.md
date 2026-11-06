# Quickstart: Main-Free Branch Publishing

This guide proves the feature end to end against throwaway repositories. It does not repeat the
manifest schema (see [contracts/manifest.md](contracts/manifest.md)) or the git history rules (see
[contracts/git-branch.md](contracts/git-branch.md)).

## Prerequisites

- Repository checkout with the feature implemented.
- `git` available and configured with `user.name` / `user.email`.
- Python dev dependencies installed:
  ```bash
  uv sync --extra dev
  ```
- A throwaway plugin repository with an `origin` remote. A local bare repository is sufficient
  for every scenario below.

## 1. Automated tests

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```

Expected: all tests pass; no `E9`, `F`, or `B` findings.

## 2. Fixture setup

Create a temporary workspace with a bare `origin` and a working clone containing a minimal plugin
(`composer.json` with `extra.shopware-plugin-class` and `version`, a `src/<Plugin>.php`, and a
clean initial commit). Point `RELEASE_DIR` at a temporary releases directory.

Suggested validation layout:

```text
workspace/
├── origin.git/          # bare remote
└── TopdataDemoSW6/      # working clone with origin -> ../origin.git
```

Expected baseline: `git status --porcelain` is empty.

## 3. No-manifest regression

1. Run `sw-build --version-increment none`.
2. Inspect `git ls-remote --heads origin`.
3. Inspect the release directory and any Slack/upload test double.

Expected:

- Paid ZIP and usual output are produced.
- No `main-free` branch exists on `origin`.
- No free ZIP, upload, or notification block exists.
- `git status --porcelain` is still empty.

## 4. First free publication

1. Add and commit `.topdata/build.yaml`:
   ```yaml
   free: {}
   ```
2. Run `sw-build --version-increment none`.
3. Run `git ls-remote --heads origin`.
4. Clone `origin` and check out `main-free` in a separate directory.

Expected:

- `refs/heads/main-free` exists.
- The branch has exactly one commit, with no parent (`git rev-list --count main-free` = 1).
- `composer.json` is at the branch root.
- The plugin class and directory are `FreeTopdataDemoSW6`.
- `release_info.txt` is present and its `Version` matches the paid build.
- `.topdata/` is absent from the branch.
- No tag was created for the snapshot.

## 5. Pull-safe append

1. Change a plugin source file, commit it, and run `sw-build --version-increment none`.
2. In the shop clone, run `git pull` only.
3. Repeat once more.

Expected:

- Each build appends exactly one commit to the remote branch.
- `git pull` fast-forwards each time; no reset or clean is required.
- The commit message contains the built version.
- The new commit's parent is the previous remote tip.

## 6. No-op and timestamp-only builds

1. Run `sw-build --version-increment none` twice against unchanged source.
2. Compare the branch tip before and after the second run.

Expected:

- The second run adds zero commits and pushes nothing.
- The builder reports that the remote tree is unchanged.
- `release_info.txt`'s `Created` timestamp alone does not force a commit.

## 7. Dirty working tree and `--skip-free`

1. Leave an uncommitted change in a tracked file.
2. Run `sw-build --version-increment none`.

Expected: non-zero exit, an actionable message, no branch update, and no upload or notification.

3. Run `sw-build --version-increment none --skip-free`.

Expected: warning that free work is skipped; the paid release proceeds; the branch is untouched.

## 8. Self-contained free variant

Use a fixture whose `composer.json` requires `topdata/topdata-foundation-sw6`, with the foundation
plugin available via `FOUNDATION_PLUGIN_PATH` or as a sibling directory.

Expected, in the published branch:

- `src/Foundation/` classes are present.
- `require` no longer lists `topdata/topdata-foundation-sw6`.
- `autoload.psr-4` contains `Topdata\Free<PluginName>\Foundation\`.
- Foundation namespaces are rewritten consistently.

With a fixture that does not require the foundation, expected: no `src/Foundation/` and no
foundation autoload entry.

## 9. Optional free archive

1. With `free: { zip: false }`, run a build and inspect the release directory.
   Expected: no `Free<PluginName>-v<version>.zip`.
2. Change the manifest to `free: { zip: true }`, commit, and rerun.
   Expected: the free ZIP exists locally and follows the normal upload/Slack behavior.
3. Add `--no-sync` and rerun the archive-enabled case.
   Expected: the free ZIP exists locally, the branch still publishes, and no upload occurs.

## 10. Failure paths

| Simulation | Expected |
|---|---|
| Remove/rename `origin` | Non-zero exit; no branch, upload, or notification |
| Point `origin` at an unreachable URL | Non-zero exit; no free history created |
| Advance the remote `main-free` tip between fetch and push (for example a hook or a second clone) | Push rejected; non-zero exit; the remote history is unchanged and not force-pushed |
| Add a local commit that races the publish | Same as above; no retry with force |
| Corrupt `.topdata/build.yaml` | Non-zero exit with a manifest error; no free work |

## 11. History and checkout invariants

After every scenario above:

```bash
git -C TopdataDemoSW6 status --porcelain          # empty
git -C TopdataDemoSW6 branch --show-current       # unchanged source branch
git -C origin.git tag                              # no free tags
git -C TopdataDemoSW6 reflog --oneline -3          # no branch switch by the publisher
```

Expected: the source checkout's branch, index, and working tree are untouched; the free branch
lives only on `origin`; no free tags exist.
