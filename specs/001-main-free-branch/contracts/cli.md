# Contract: `sw-build` CLI behavior

**Entry point**: `sw-build` → `topdata_package_release_builder.cli:main`.

## New option

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--skip-free` | flag | off | Disable all free work even when `.topdata/build.yaml` enables it |

## Ordering contract

For an opted-in repository, the build order MUST be:

```text
git status / optional staging
→ asset verification
→ version selection and (if requested) version bump commit + tag + push
→ clean-working-tree check for free work
→ free variant copy + transform + foundation injection + release record
→ free branch publication (fetch / compare / commit / push)
→ optional free ZIP creation and upload
→ paid payload copy + ZIP creation
→ manual documentation publishing
→ paid remote sync
→ optional manual variant creation/upload
→ Slack notification (main, manual variant, optional free archive)
→ success summary
```

The free branch publication MUST finish before manual publishing, paid uploads, and any Slack
notification.

## Exit-code contract

| Situation | Exit | Later steps |
|---|---|---|
| No manifest | 0 (normal build) | Paid release proceeds exactly as before |
| Manifest disabled (`free` absent) | 0 | Paid release proceeds exactly as before |
| Free publish succeeds or is a no-op | 0 | Paid release continues |
| `--skip-free` with manifest enabled | 0 | Paid release continues; warning printed |
| Manifest invalid | non-zero | No manual publish, no upload, no notification |
| Dirty working tree for free work | non-zero | No free work, no manual publish, no upload, no notification |
| `origin` missing / unreachable | non-zero | No free work, no manual publish, no upload, no notification |
| Fetch, commit, or push fails | non-zero | No free work continuation, no manual publish, no upload, no notification |
| Push rejected because the branch moved | non-zero | No retry and no force-push |

## User-visible messages

- When the manifest is enabled and `--skip-free` is used: a warning that free work is skipped.
- When the branch is created or updated: the branch name and commit SHA.
- When there is nothing to publish: a message that the remote tree is unchanged.
- All fatal errors: a clear reason and a non-zero exit via the existing top-level abort path.

## Interaction with existing switches

| Switch | Effect on free work |
|---|---|
| `--no-sync` | Free branch still publishes; free ZIP stays local; no upload |
| `--notify-slack` | Slack may reference the free archive when `free.zip` is true |
| `--variant-prefix/--variant-suffix` | Independent of free work; both artifacts may exist |
| `--with-foundation` | Same injection decision is reused for the free variant |

## No-manifest regression

On a repository without `.topdata/build.yaml`, `sw-build` MUST produce the same archives, uploads,
notifications, and exit behavior as before this feature. In particular it MUST NOT create a
branch, make a network call for free publication, or add a free section to the success summary.
