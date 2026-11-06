# Contract: Python module API

This is an internal CLI library contract. It exists so the manifest parser and the git publisher
can be tested independently and so the CLI orchestration stays thin.

## `topdata_package_release_builder.free_manifest`

```python
@dataclass(frozen=True)
class FreeManifest:
    enabled: bool
    path: Path | None
    branch: str
    zip: bool


class FreeManifestError(ValueError):
    """Raised when a present manifest is invalid."""


def load_free_manifest(plugin_root: str | Path) -> FreeManifest:
    """Load and validate <plugin_root>/.topdata/build.yaml.

    Never raises for a missing file or an empty document; returns a disabled
    manifest. Raises FreeManifestError for invalid YAML, a non-mapping root, a
    non-mapping free value, an invalid branch, or a non-boolean zip.
    """
```

**Guarantees**

- No network access and no mutation of the plugin tree.
- Branch validation uses `git check-ref-format refs/heads/<branch>` in addition to explicit
  whitespace/`..` checks.
- `free: null` and `free: {}` produce `enabled=True` with defaults.

## `topdata_package_release_builder.free_branch`

```python
@dataclass(frozen=True)
class FreeSnapshot:
    branch: str
    version: str
    previous_tip: str | None
    payload_tree: str
    commit: str | None
    committed: bool
    pushed: bool
    timestamp_only: bool


def build_free_payload(
    *,
    source_dir: str | Path,
    plugin_name: str,
    version: str,
    branch: str,
    commit: str,
    foundation_plugin_path: str | Path | None,
    assets: dict | None,
    console: Console | None,
) -> tuple[str, Path]:
    """Return (free_name, payload_root) in a caller-owned temporary directory."""
```

**Guarantees**

- Reuses `copy_plugin_files`, `transform_to_variant`, `inject_foundation_code`, and
  `create_release_info`.
- Adds `.topdata` to the release exclusions.
- Never writes into `source_dir`.
- Injects foundation only when `foundation_plugin_path` is not `None`.

```python
def publish_free_branch(
    *,
    repo_root: str | Path,
    payload_root: str | Path,
    branch: str,
    version: str,
    console: Console | None,
) -> FreeSnapshot:
    """Publish payload_root as an append-only snapshot commit on origin/<branch>."""
```

**Guarantees / errors**

- Raises `FreePublishError` when the working tree is dirty, `origin` is missing or unreachable,
  the branch name is invalid, git plumbing fails, or the push is rejected.
- Does not switch branches, does not create a local branch, and never force-pushes.
- Does not create tags.
- On an identical payload (timestamp ignored), returns `committed=False`, `pushed=False`.
- On first publication, `previous_tip=None` and the commit has no parent.
- On later publications, the commit's only parent is `previous_tip`.

## Existing modules (narrow changes)

```python
# plugin.py
def copy_plugin_files(
    temp_dir, plugin_name, source_dir='.', verbose=False, console=None,
    *, extra_excludes: Iterable[str] = (),
) -> str: ...

# slack.py
def send_release_notification(
    ..., free_info: dict | None = None,
) -> bool: ...
```

`extra_excludes` is appended to the existing ignore list; default behavior is unchanged.
`free_info` is rendered as an optional block alongside the existing main and variant blocks.

## CLI integration

```python
# cli.py — new option
@click.option('--skip-free', is_flag=True, help='Disable free-branch publishing even when enabled by .topdata/build.yaml.')
```

The CLI MUST catch `FreeManifestError` and `FreePublishError` at the existing error boundary,
print a clear message, and abort with a non-zero exit before manual publishing, uploads, or
notifications.
