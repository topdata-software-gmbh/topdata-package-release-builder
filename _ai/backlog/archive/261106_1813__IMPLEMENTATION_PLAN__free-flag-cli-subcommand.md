---
filename: "_ai/backlog/active/261106_1813__IMPLEMENTATION_PLAN__free-flag-cli-subcommand.md"
title: "CLI subcommands to enable and disable the free flag in .topdata/build.yaml"
createdAt: 2026-11-06 18:13
updatedAt: 2026-11-06 18:13
status: completed
completedAt: 2026-11-06 18:25
priority: medium
tags: [cli, click, manifest, free-branch, config, dx]
estimatedComplexity: moderate
documentRevision: 1
sourceSpec: "specs/001-main-free-branch/spec.md"
sourceHandoff: ""
sourceAdrs: []
documentType: IMPLEMENTATION_PLAN
---

# CLI subcommands to enable and disable the free flag

## 1. Problem

The main-free branch feature is opt-in through a committed `.topdata/build.yaml` manifest.
The current workflow has no way to create or remove that manifest from the tool itself. A real
case exposed the gap: running `sw-build` in
`/topdata/clones/focus/vol/www/custom/plugins/topdata-category-filter-sw6` produced no
`main-free` branch because the repository has no `.topdata/` directory at all. The build was
correct — the feature was simply never opted in.

Today a maintainer must hand-create a YAML file and remember the exact shape (`free: {}`),
the default branch (`main-free`) and the optional `free.zip` flag. Hand-editing is error-prone:
`free: true` and `free: false` are rejected by the loader (the value must be a mapping or
`null`), and a typo in the branch name is only discovered on the next build.

The request: add a subcommand that adds/removes the free flag in the Topdata meta config.

## 2. Executive summary

Add a `sw-build free` subcommand group with `enable`, `disable` and `status` commands. They
operate on the existing per-repository meta config `.topdata/build.yaml`, reuse the validated
`free_manifest` loader, and write the file atomically while preserving unrelated keys.

The existing `sw-build [options]` build invocation must keep working unchanged. The root Click
entry point becomes a group with a default `build` command, so all legacy option forms route to
the build exactly as before.

No commit, tag, push or build is performed by the new commands; they only mutate the manifest
and print the path and the next step.

## 3. Open questions / assumptions to confirm

These are blockers only if the assumption is wrong.

| # | Question | Assumption used in this plan |
|---|---|---|
| Q1 | Does "topdata meta config" mean the per-plugin `.topdata/build.yaml` introduced with the free-branch feature, or a different file (e.g. a global `~/.config/topdata/*` or a separate `meta.yaml`)? | It means `<plugin-root>/.topdata/build.yaml`. No other meta-config file exists in the repository or the inspected plugin checkout. |
| Q2 | Does "remove the free flag" mean delete the `free` key, or write `free: false`? | Delete the `free` key. The current manifest contract rejects a boolean `free`; deleting the key is the canonical disabled state. |
| Q3 | Must YAML comments survive an enable/disable edit? | No. PyYAML is the existing parser; round-tripping with `safe_dump` preserves keys/values but drops comments. If comments are required, the plan must switch to a text-surgical editor or `ruamel.yaml` (out of scope here). |
| Q4 | Should `enable`/`disable` auto-commit the manifest? | No. The tool mutates the file, prints the path and the suggested `git add`/`git commit`; committing remains a human/release decision. |

## 4. Design decisions & rejected alternatives

| Decision | Rationale | Rejected alternative |
|---|---|---|
| `sw-build free enable\|disable\|status` command group | Verb-oriented, discoverable, leaves room for future `branch`/`zip` management. | A single positional magic argument on `sw-build` (`sw-build free on`), which is less discoverable and brittle to parse. |
| Keep `.topdata/build.yaml` as the only meta config | It already exists, is validated, and is excluded from release payloads. | Introduce `.topdata/meta.yaml` and migrate the parser; unnecessary churn and a second source of truth. |
| Mutate via PyYAML `safe_load` → `safe_dump(sort_keys=False)` | Reuses the trusted loader, preserves unrelated keys, no new dependency. | Text-surgical editing (comment-preserving but fragile with indentation/flow style). |
| Atomic write with a sibling temp file + `os.replace` | A failed write must never truncate a valid manifest. | Direct `write_text` (can leave a half-written file on disk-full/interrupt). |
| Enable writes `free: {}` or merges into an existing mapping | Works with the current loader, which treats `null`/`{}` as enabled and rejects booleans. | Enable writes `free: true`; would require a parser contract change and break backward compatibility with the published spec. |
| Disable deletes the `free` key; deletes the file and empty `.topdata/` when nothing else remains | Clean removal, no dead config. Unknown keys are preserved. | Leave a disabled stub or write `free: false`; both keep a key that adds no value and `false` is currently invalid. |
| Root Click `DefaultGroup` with default `build` command | Preserves every existing `sw-build [options]` invocation and adds subcommands. | Requiring `sw-build build ...`; a breaking change. |
| New commands live in `commands/free_cmd.py` | Matches the project Python convention for subcommands; keeps `cli.py` focused on orchestration. | Growing `cli.py` by another command group. |

The source design record `specs/SPEC__261106-1__main-free-branch-publishing.md` listed
"Creating or editing `.topdata/build.yaml` automatically" as a **non-goal** (line 40). This plan
intentionally supersedes that non-goal because the user explicitly requested the editing
command. No other requirement from `specs/001-main-free-branch/spec.md` changes.

## 5. Project environment

- Project Name: Topdata Package Release Builder
- Frontend root: (none — Python CLI only)
- Backend root: `topdata_package_release_builder/`
- CLI entry point: `sw-build = topdata_package_release_builder.cli:main` (`pyproject.toml`)
- Test command: `uv run --extra dev pytest`
- Lint command: `uv run --extra dev ruff check .`
- Git workflow: commit directly on `main`; no feature branch or pull request.

## 6. Traceability

No new formal spec exists. The request extends the already implemented feature; every new
observable behavior below is given a local acceptance criterion so implementation can be
checked.

| Local AC | Behavior | Related source requirement |
|---|---|---|
| AC-001 | `sw-build free enable` creates `.topdata/build.yaml` with an enabled `free` mapping and defaults. | FR-001, FR-002 |
| AC-002 | `sw-build free enable --branch X --zip` writes the requested values and validates the branch first. | FR-002, FR-018, FR-020 |
| AC-003 | Enable preserves unrelated manifest keys and existing `free` options not overridden. | FR-001 (forward-compatible unknown keys) |
| AC-004 | `sw-build free disable` removes the `free` key; removes the file and empty `.topdata/` when no other keys remain. | Inverse of FR-001 |
| AC-005 | `sw-build free status` reports enabled/disabled, branch, zip and the manifest path. | FR-001, FR-002, FR-018 |
| AC-006 | An invalid existing manifest is never mutated; the command exits non-zero with the parser error. | FR-020 |
| AC-007 | `sw-build [options]` still runs the build exactly as before; `sw-build free ...` routes to the new group. | SC-002 (no regression) |
| AC-008 | The manifest edit is atomic (temp file + `os.replace`). | FR-020 robustness |
| AC-009 | No build, commit, tag, push, upload or Slack call happens in the new commands. | FR-015, FR-016 scope guard |

## 7. Phase 1 — Manifest mutation layer

**Goal**: Add write operations next to the existing read/validate logic.

### [MODIFY] `topdata_package_release_builder/free_manifest.py`

Add imports and public functions. Keep the existing `FreeManifest`, `FreeManifestError`,
`DEFAULT_BRANCH`, `load_free_manifest`, `_validate_branch`, `_validate_zip` untouched.

```python
# [MODIFY] topdata_package_release_builder/free_manifest.py
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml
```

Add a document reader that mirrors the validation rules of `load_free_manifest` but returns
the whole mapping so unrelated keys survive:

```python
# [MODIFY] topdata_package_release_builder/free_manifest.py

def _read_document(plugin_root: str | Path) -> tuple[dict[str, object], Path]:
    """Return the manifest mapping and its path.

    A missing or empty file yields an empty mapping. A non-mapping root aborts.
    """
    path = Path(plugin_root) / MANIFEST_RELATIVE_PATH
    if not path.is_file():
        return {}, path

    try:
        document = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise FreeManifestError(f"Invalid YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise FreeManifestError(f"Could not read manifest {path}: {exc}") from exc

    if document is None:
        return {}, path
    if not isinstance(document, dict):
        raise FreeManifestError(
            f"Invalid manifest {path}: the root document must be a mapping"
        )
    return document, path


def _serialize_document(document: dict[str, object]) -> str:
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)


def _write_document(document: dict[str, object], path: Path) -> None:
    """Atomically replace the manifest, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _serialize_document(document)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix='.build-', suffix='.yaml.tmp'
    )
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            handle.write(payload)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
```

Public enable/disable operations:

```python
# [MODIFY] topdata_package_release_builder/free_manifest.py

def enable_free(
    plugin_root: str | Path = '.',
    *,
    branch: str | None = None,
    zip_enabled: bool | None = None,
) -> FreeManifest:
    """Enable free publishing, merging into an existing free mapping.

    ``branch`` and ``zip_enabled`` are only written when supplied; existing
    values are preserved otherwise. The file is written atomically and the
    result is re-read through the normal validator.
    """
    document, path = _read_document(plugin_root)

    free = document.get('free')
    if free is None:
        free = {}
    if not isinstance(free, dict):
        raise FreeManifestError(f"Invalid manifest {path}: 'free' must be a mapping")

    updated = dict(free)
    if branch is not None:
        _validate_branch(branch, path)
        updated['branch'] = branch
    if zip_enabled is not None:
        _validate_zip(zip_enabled, path)
        updated['zip'] = zip_enabled

    document['free'] = updated
    if _serialize_document(document) != (path.read_text(encoding='utf-8') if path.is_file() else ''):
        _write_document(document, path)

    return load_free_manifest(plugin_root)


def disable_free(plugin_root: str | Path = '.') -> FreeManifest:
    """Remove the free key; clean up the file/directory when nothing remains."""
    document, path = _read_document(plugin_root)
    if 'free' not in document:
        return load_free_manifest(plugin_root)

    del document['free']
    if document:
        _write_document(document, path)
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        else:
            try:
                path.parent.rmdir()
            except OSError:
                pass

    return load_free_manifest(plugin_root)
```

**Notes**

- The idempotence comparison uses the serialized form. A second `enable` with the same values
  performs no write (stable mtime, no noisy diff).
- `_validate_zip` already rejects non-booleans; passing `zip_enabled=None` means "do not touch".
- `disable_free` does not validate the free value first; if the manifest is invalid YAML,
  `_read_document` raises and the file is left untouched.

### Phase 1 tests

### [NEW FILE] `tests/test_free_manifest_mutation.py`

Cover:

1. `enable_free` on a missing file creates `.topdata/build.yaml` containing `free: {}` and
   `load_free_manifest(...).enabled is True`, `branch == 'main-free'`, `zip is False`.
2. `enable_free(branch='free-latest', zip_enabled=True)` writes both values.
3. Enabling over an existing document preserves `other: value` and an existing `free.branch`
   when `branch=None`.
4. Enabling twice is idempotent: file bytes and `mtime_ns` are unchanged.
5. An invalid branch/call leaves the directory untouched (no file created).
6. An existing invalid manifest (`free: [unclosed`) raises and is not rewritten.
7. `disable_free` removes the `free` key but keeps other keys.
8. `disable_free` on a free-only file deletes the file and the empty `.topdata/` directory.
9. `disable_free` is a no-op when the file or key is absent.
10. `disable_free` on invalid YAML raises and does not modify the file.

## 8. Phase 2 — `free` command group

**Goal**: Provide `enable`, `disable`, `status` with clear, non-destructive output.

### [NEW FILE] `topdata_package_release_builder/commands/__init__.py`

```python
"""CLI command groups for the release builder."""
```

### [NEW FILE] `topdata_package_release_builder/commands/free_cmd.py`

```python
# [NEW FILE] topdata_package_release_builder/commands/free_cmd.py
"""`sw-build free` subcommands: manage the free-branch opt-in manifest."""
from __future__ import annotations

import click
from rich.console import Console

from ..free_manifest import (
    FreeManifestError,
    disable_free,
    enable_free,
    load_free_manifest,
)

console = Console()


@click.group('free')
def free_group() -> None:
    """Manage free-branch publishing in .topdata/build.yaml."""


@free_group.command('enable')
@click.option('--source-dir', default='.', help='Plugin source directory (default: current directory).')
@click.option('--branch', default=None, help='Target branch on origin (default: main-free).')
@click.option('--zip/--no-zip', 'zip_enabled', default=None,
              help='Also create/upload a free ZIP on each build.')
def enable_command(source_dir: str, branch: str | None, zip_enabled: bool | None) -> None:
    """Add the free flag to the Topdata meta config."""
    try:
        manifest = enable_free(source_dir, branch=branch, zip_enabled=zip_enabled)
    except FreeManifestError as exc:
        raise click.ClickException(str(exc)) from exc

    path = manifest.path
    console.print(f'[green]✓ Free branch publishing enabled[/] ({path})')
    console.print(f'  Branch: {manifest.branch}')
    console.print(f'  ZIP:    {"enabled" if manifest.zip else "disabled"}')
    console.print('[dim]Next: git add .topdata/build.yaml && git commit -m "chore: enable free branch"[/]')


@free_group.command('disable')
@click.option('--source-dir', default='.', help='Plugin source directory (default: current directory).')
def disable_command(source_dir: str) -> None:
    """Remove the free flag from the Topdata meta config."""
    try:
        manifest = disable_free(source_dir)
    except FreeManifestError as exc:
        raise click.ClickException(str(exc)) from exc

    console.print('[green]✓ Free branch publishing is disabled[/]')
    if manifest.path is not None:
        console.print(f'[dim]Kept: {manifest.path}[/]')


@free_group.command('status')
@click.option('--source-dir', default='.', help='Plugin source directory (default: current directory).')
def status_command(source_dir: str) -> None:
    """Show whether free-branch publishing is enabled."""
    try:
        manifest = load_free_manifest(source_dir)
    except FreeManifestError as exc:
        raise click.ClickException(str(exc)) from exc

    if not manifest.enabled:
        console.print('[yellow]Free branch publishing is disabled[/]')
        return

    console.print('[green]Free branch publishing is enabled[/]')
    console.print(f'  Manifest: {manifest.path}')
    console.print(f'  Branch:   {manifest.branch}')
    console.print(f'  ZIP:      {"enabled" if manifest.zip else "disabled"}')
```

**Behavior rules**

- `enable` with no flags on an absent file writes `free: {}`.
- `enable --branch` validates with `git check-ref-format` before writing.
- `enable --zip` and `enable --no-zip` are the only ways to change the ZIP flag; no flag
  preserves the current value.
- `disable` is idempotent and prints success either way.
- `status` never writes.
- All errors go through `click.ClickException` → exit code 1 with a clear message.

### Phase 2 tests

### [NEW FILE] `tests/test_free_cli_commands.py`

Use `click.testing.CliRunner` and `tmp_path`:

1. `free enable --source-dir tmp` → exit 0, file exists, `load_free_manifest` enabled.
2. `free enable --branch free-latest --zip` → branch and zip written.
3. `free enable --branch 'bad~branch'` → exit non-zero, no file created.
4. `free disable` after enable → exit 0, file gone.
5. `free disable` twice → both exit 0.
6. `free status` output contains `enabled`, branch and ZIP state; after disable contains
   `disabled`.
7. Invalid existing manifest → all three commands exit non-zero and the file bytes are
   unchanged.

## 9. Phase 3 — Preserve the legacy build invocation

**Goal**: `sw-build [options]` must keep working while `sw-build free ...` is added.

### [MODIFY] `topdata_package_release_builder/cli.py`

Add the import and the default group next to the existing command:

```python
# [MODIFY] topdata_package_release_builder/cli.py (imports)
from .commands.free_cmd import free_group
```

Add the group class and root command at the end of the module, replacing the `main()` body:

```python
# [MODIFY] topdata_package_release_builder/cli.py

class DefaultGroup(click.Group):
    """Click group that treats a leading option as the default `build` command."""

    def __init__(self, *args, default_command: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_command = default_command

    def resolve_command(self, ctx, args):
        if not args or args[0].startswith(('-h', '--help')):
            return super().resolve_command(ctx, args)
        if args[0] in self.commands or not args[0].startswith('-'):
            return super().resolve_command(ctx, args)
        return super().resolve_command(ctx, [self.default_command, *args])


@click.group(
    cls=DefaultGroup,
    default_command='build',
    invoke_without_command=True,
    context_settings=dict(help_option_names=['-h', '--help']),
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Build and package Shopware 6 plugins."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(build_plugin)


cli.add_command(build_plugin, 'build')
cli.add_command(free_group)


def main() -> None:
    """Entry point for the CLI."""
    cli()
```

**Routing matrix**

| Invocation | Route |
|---|---|
| `sw-build` | Root callback → `build` with option defaults |
| `sw-build --version-increment none` | `DefaultGroup` prepends `build` |
| `sw-build --source-dir X --no-sync` | Prepends `build` |
| `sw-build build --version-increment none` | Explicit build command |
| `sw-build free enable --source-dir X` | `free` group |
| `sw-build --help` | Group help listing `build` and `free` |
| `sw-build free --help` | Free group help |

### Phase 3 tests

Add to `tests/test_free_cli_commands.py`:

1. `sw-build --version-increment none --source-dir X --output-dir Y` exits 0 and reaches the
   build callback. Monkeypatch `cli.build_plugin.callback` to a recorder instead of running a
   real build.
2. `sw-build` with no arguments reaches the same callback.
3. `sw-build free status` reaches the free group and does not call the build callback.
4. The existing 143-test suite still passes; in particular `tests/test_free_cli.py`
   continues to import and invoke `cli.build_plugin` unchanged.

## 10. Phase 4 — Documentation

### [MODIFY] `README.md`

- In **Free Branch Publishing**, add the manifest-management commands before the YAML example:

```markdown
Enable or disable the opt-in from the plugin checkout:

```bash
sw-build free enable                    # writes `.topdata/build.yaml` with `free: {}`
sw-build free enable --branch main-free --zip
sw-build free disable                   # removes the free key
sw-build free status
```
```

- Note that the command edits a committed file; commit the change yourself.

### [MODIFY] `manual/30-configuration.de.md` and `manual/30-configuration.en.md`

Add a short subsection referencing the commands:

```markdown
Das Manifest wird am einfachsten über die CLI gepflegt:

```bash
sw-build free enable [--branch main-free] [--zip]
sw-build free disable
sw-build free status
```
```

Keep the German/English pair in sync.

### [MODIFY] `manual/40-usage.de.md` and `manual/40-usage.en.md`

Add a "Free-Flag verwalten" / "Managing the Free Flag" subsection under the free-branch section
with the three commands and their effect on the YAML.

## 11. Phase 5 — Housekeeping and implementation report

### [NEW FILE] `CHANGELOG.md`

The repository has no changelog. Create one with a Keep-a-Changelog-style `Unreleased` entry:

```markdown
# Changelog

## Unreleased

### Added
- `sw-build free enable|disable|status` subcommands to manage the `.topdata/build.yaml`
  free-branch opt-in without hand-editing YAML.
```

### `.gitignore`

No change expected: the new files are ordinary `.py`, `.md` and test files. `.topdata/build.yaml`
must remain tracked; do **not** add `.topdata/` to `.gitignore`.

### [NEW FILE] `_ai/backlog/reports/261106_1813__IMPLEMENTATION_REPORT__free-flag-cli-subcommand.md`

After implementation, write the report with the required frontmatter and sections:

1. Summary
2. Files changed (new/modified/deleted)
3. Key changes
4. Deviations from plan
5. Technical decisions
6. Testing notes (`uv run --extra dev pytest`, `uv run --extra dev ruff check .`)
7. Usage examples for `sw-build free enable|disable|status`
8. Documentation updates
9. Next steps

Set `status: completed`, `planFile` to this plan, `specFile` to
`specs/001-main-free-branch/spec.md`, and count files accurately.

## 12. Verification checklist

Run after each implementation phase:

```bash
uv run --extra dev pytest tests/test_free_manifest_mutation.py -q
uv run --extra dev pytest tests/test_free_cli_commands.py -q
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```

Manual smoke test in a throwaway plugin clone:

```bash
uv run sw-build free status                 # disabled
uv run sw-build free enable --zip
git diff -- .topdata/build.yaml              # free: {zip: true}
uv run sw-build free status                  # enabled, branch main-free, ZIP enabled
git add .topdata/build.yaml && git commit -m "chore: enable free branch"
uv run sw-build --version-increment none     # publishes main-free
uv run sw-build free disable
git diff -- .topdata/build.yaml              # free key removed (file deleted if empty)
```

Acceptance is reached when all local ACs in §6 are covered by a test and the manual smoke test
produces a `main-free` branch and then removes the opt-in cleanly.
