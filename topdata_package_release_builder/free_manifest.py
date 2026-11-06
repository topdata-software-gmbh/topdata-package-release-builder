"""Safe parsing and validation for the ``.topdata/build.yaml`` manifest.

The manifest is committed build metadata, not plugin code. It is untrusted
input: a present but malformed document aborts the build instead of silently
disabling free branch publishing.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

MANIFEST_RELATIVE_PATH = Path('.topdata') / 'build.yaml'
DEFAULT_BRANCH = 'main-free'


class FreeManifestError(ValueError):
    """Raised when a present manifest is invalid."""


@dataclass(frozen=True)
class FreeManifest:
    """Validated view of the free section of the build manifest."""

    enabled: bool
    path: Path | None
    branch: str
    zip: bool


def _disabled(path: Path | None = None) -> FreeManifest:
    return FreeManifest(enabled=False, path=path, branch=DEFAULT_BRANCH, zip=False)


def _validate_branch(value: object, manifest_path: Path) -> str:
    if not isinstance(value, str):
        raise FreeManifestError(
            f"Invalid free.branch in {manifest_path}: expected a string, got {type(value).__name__}"
        )
    branch = value
    if not branch:
        raise FreeManifestError(f"Invalid free.branch in {manifest_path}: must not be empty")
    if branch != branch.strip():
        raise FreeManifestError(
            f"Invalid free.branch in {manifest_path}: must not have leading or trailing whitespace"
        )
    if any(character.isspace() for character in branch):
        raise FreeManifestError(f"Invalid free.branch in {manifest_path}: must not contain whitespace")
    if '..' in branch:
        raise FreeManifestError(f"Invalid free.branch in {manifest_path}: must not contain '..'")

    try:
        result = subprocess.run(
            ['git', 'check-ref-format', f'refs/heads/{branch}'],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - git is a hard dependency
        raise FreeManifestError(
            f"Cannot validate free.branch in {manifest_path}: git executable not found"
        ) from exc

    if result.returncode != 0:
        raise FreeManifestError(
            f"Invalid free.branch in {manifest_path}: '{branch}' is not a valid git branch name"
        )
    return branch


def _validate_zip(value: object, manifest_path: Path) -> bool:
    if not isinstance(value, bool):
        raise FreeManifestError(
            f"Invalid free.zip in {manifest_path}: expected a boolean, got {type(value).__name__}"
        )
    return value


def load_free_manifest(plugin_root: str | Path = '.') -> FreeManifest:
    """Load and validate ``<plugin_root>/.topdata/build.yaml``.

    A missing file or an empty/comments-only document returns a disabled
    manifest. ``free: null`` and ``free: {}`` enable it with defaults.
    Any other malformed shape raises :class:`FreeManifestError`.
    """
    path = Path(plugin_root) / MANIFEST_RELATIVE_PATH
    if not path.is_file():
        return _disabled()

    try:
        document = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise FreeManifestError(f"Invalid YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise FreeManifestError(f"Could not read manifest {path}: {exc}") from exc

    if document is None:
        return _disabled(path)
    if not isinstance(document, dict):
        raise FreeManifestError(
            f"Invalid manifest {path}: the root document must be a mapping"
        )
    if 'free' not in document:
        return _disabled(path)

    free = document['free']
    if free is None:
        free = {}
    if not isinstance(free, dict):
        raise FreeManifestError(
            f"Invalid manifest {path}: 'free' must be a mapping"
        )

    branch = _validate_branch(free.get('branch', DEFAULT_BRANCH), path)
    zip_enabled = _validate_zip(free.get('zip', False), path)

    return FreeManifest(enabled=True, path=path, branch=branch, zip=zip_enabled)


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
