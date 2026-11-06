# Phase 1 Data Model: Main-Free Branch Publishing

This feature has no database. The entities below are parsed configuration, in-memory build
values, filesystem payloads, and git objects. Field names in backticks are the Python-facing
names; the manifest keys are the YAML keys.

## 1. FreeManifest

**Source**: committed file `<plugin-root>/.topdata/build.yaml`, `free` mapping.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | `bool` | `False` when file/key absent | Whether free work runs at all |
| `path` | `Path \| None` | `None` when absent | Manifest path used for messages |
| `branch` | `str` | `"main-free"` | Target branch on `origin` |
| `zip` | `bool` | `False` | Whether to produce/upload a free ZIP |

**YAML shape**

```yaml
free:
  branch: main-free   # optional
  zip: false          # optional
```

**Validation rules**

| Rule | Outcome | Requirement |
|---|---|---|
| File absent | disabled, no error | FR-001, SC-002 |
| YAML empty (`None`) or no `free` key | disabled, no error | FR-001 |
| Root document is not a mapping | abort with clear error | FR-020 |
| `free` is `null` or `{}` | enabled with defaults | Edge case: empty mapping |
| `free` is not a mapping | abort with clear error | FR-020 |
| `free.branch` absent | `main-free` | FR-002 |
| `free.branch` not a string / empty / whitespace-padded / contains `..` | abort | FR-020, edge case |
| `free.branch` rejected by `git check-ref-format refs/heads/<branch>` | abort | FR-020, edge case |
| `free.zip` absent | `False` | FR-018 |
| `free.zip` not a boolean | abort | FR-020 |

**Notes**

- Unknown keys are ignored for forward compatibility; they do not affect behavior.
- A comments-only file parses as `None` and therefore disables the feature rather than aborting.
- The manifest itself must never appear in the published payload (FR-006).

## 2. FreePayload

**Produced in**: a temporary directory; never in the source checkout.

| Field | Type | Meaning |
|---|---|---|
| `plugin_name` | `str` | Original plugin name read from composer |
| `free_name` | `str` | `Free<plugin_name>` (FR-003) |
| `free_plugin_dir` | `Path` | Root of the transformed plugin tree (branch root) |
| `version` | `str` | Same version as the paid build (FR-014) |
| `branch` | `str` | Source git branch recorded in provenance |
| `commit` | `str` | Source git commit recorded in provenance |
| `release_info` | `str` | Machine-readable release record, including `Created` |
| `foundation_injected` | `bool` | Whether foundation code was injected |

**Construction order**

1. Copy the source plugin with the existing release exclusions **plus** `.topdata` (FR-006).
2. Apply `transform_to_variant(prefix="Free", suffix="")` (FR-003, FR-004).
3. If the build's existing injection decision is true, run `inject_foundation_code` (FR-005).
4. Write `release_info.txt` at the payload root (FR-006, FR-007, FR-023).

**Invariants**

- `free_plugin_dir.name == free_name`.
- The plugin root is the payload root: `composer.json` is at the payload root (FR-007).
- No `.topdata/`, `.git*`, build-tool state, tests, or AI/dev files (FR-006, SC-003).
- `require` has no `topdata/topdata-foundation-sw6` when foundation was injected (FR-005).
- `autoload.psr-4` registers `Topdata\<free_name>\Foundation\` when foundation was injected.
- `release_info.txt` names `free_name` and the same `version`.

## 3. FreeSnapshot

**Represents** one publication attempt/result.

| Field | Type | Meaning |
|---|---|---|
| `branch` | `str` | Target branch on `origin` |
| `version` | `str` | Version included in the commit message |
| `previous_tip` | `str \| None` | Fetched remote tip; `None` for the first snapshot |
| `payload_tree` | `str` | Tree object SHA of the payload |
| `commit` | `str \| None` | New commit SHA; `None` on a no-op |
| `committed` | `bool` | Whether a new commit was created |
| `pushed` | `bool` | Whether a push was performed |
| `timestamp_only` | `bool` | True when the only difference was `release_info.txt` `Created` |

**State transitions**

```text
[manifest disabled] --build--> no free work (end)
[manifest enabled] --clean tree?--> no  --> abort (non-zero, no uploads/notifications)
[manifest enabled] --clean tree?--> yes --> build payload
payload built --> remote origin missing/unreachable --> abort
payload built --> branch absent --> orphan snapshot commit --> push --> success
payload built --> branch exists, tree identical (timestamp ignored) --> no-op --> success
payload built --> branch exists, tree differs --> append snapshot on fetched tip --> push --> success
payload built --> branch exists, push rejected because tip moved --> abort (no force)
```

**Invariants**

- `previous_tip is None` ⇔ first snapshot has no parent.
- `committed == False` ⇔ `pushed == False` ⇔ `commit is None`.
- A commit message always contains `v<version>` (FR-013).
- No tag is created (FR-023, SC-010).
- Published history is never rewritten; each non-first commit has the fetched tip as its single
  parent (FR-011).
- The source working tree and index are unchanged by publication.

## 4. FreeArchive

**Optional artifact**, present only when `FreeManifest.zip` is true.

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | `Free<plugin_name>` |
| `zip_name` | `str` | `<free_name>-v<version>.zip` |
| `zip_path` | `Path` | Local path under the release directory |
| `sync_status` | `bool \| None` | `True` uploaded, `False` disabled by `--no-sync`, `None` no remote |
| `download_url` | `str \| None` | Derived from the rsync path when available |
| `zip_file_rsync_path` | `str \| None` | Remote path returned by rsync |

**Rules**

- `zip == False`: no file written, no upload, no Slack mention (FR-018, SC-005).
- `zip == True`: archive created and handled like the paid archive (FR-019).
- `zip == True` and `--no-sync`: local archive exists, no upload (FR-019, FR-022).
- The upload-disable switch never suppresses branch publication (FR-022, SC-008).

## 5. Relationship to existing entities

| Existing entity | Relationship |
|---|---|
| Plugin `composer.json` | Source of plugin name/version; transformed in the free payload |
| Release ZIP payload | Shares exclusions; free payload adds `.topdata` and moves the root to branch root |
| `release_info.txt` | Reused format; `Created` ignored for change detection, included in the commit |
| Manual variant (`--variant-*`) | Independent artifact; free variant is built automatically with fixed `Free` prefix |
| Foundation plugin | Source of injected code; located via `FOUNDATION_PLUGIN_PATH` or sibling directory |
| `origin` remote | Sole publication target; never a mirror or secondary remote |
| `release_info.txt` `Created` | The only field excluded from content comparison (FR-012) |

## 6. Requirement coverage map

| Requirement | Entity / rule |
|---|---|
| FR-001, FR-002 | FreeManifest enablement + `branch` |
| FR-003, FR-004 | FreePayload `free_name`, transform step |
| FR-005 | FreePayload foundation injection |
| FR-006, FR-007 | FreePayload exclusions + root layout |
| FR-008, FR-009, FR-011 | FreeSnapshot `previous_tip`, parent rule |
| FR-010 | CLI invocation (publish every build while enabled) |
| FR-012 | FreeSnapshot tree comparison + `timestamp_only` |
| FR-013, FR-014, FR-023 | FreeSnapshot commit message/version, no tag |
| FR-015, FR-016 | CLI ordering and abort path |
| FR-017 | `--skip-free` |
| FR-018, FR-019 | FreeArchive `zip` rules |
| FR-020 | FreeManifest validation + remote checks |
| FR-021 | Clean-tree precondition |
| FR-022 | `--no-sync` interaction |
