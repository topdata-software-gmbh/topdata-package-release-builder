"""Tests for writing the ``.topdata/build.yaml`` free flag."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from topdata_package_release_builder.free_manifest import (
    FreeManifestError,
    disable_free,
    enable_free,
    load_free_manifest,
)


def _write(plugin_root: Path, content: str) -> Path:
    path = plugin_root / '.topdata' / 'build.yaml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _read(plugin_root: Path) -> dict:
    path = plugin_root / '.topdata' / 'build.yaml'
    return yaml.safe_load(path.read_text(encoding='utf-8'))


# ---------------------------------------------------------------------------
# enable
# ---------------------------------------------------------------------------


def test_enable_creates_manifest_with_defaults(tmp_path: Path) -> None:
    manifest = enable_free(tmp_path)

    path = tmp_path / '.topdata' / 'build.yaml'
    assert path.is_file()
    assert _read(tmp_path) == {'free': {}}
    assert manifest.enabled is True
    assert manifest.branch == 'main-free'
    assert manifest.zip is False
    assert manifest.path == path


def test_enable_writes_requested_branch_and_zip(tmp_path: Path) -> None:
    manifest = enable_free(tmp_path, branch='free-latest', zip_enabled=True)

    assert _read(tmp_path) == {'free': {'branch': 'free-latest', 'zip': True}}
    assert manifest.branch == 'free-latest'
    assert manifest.zip is True


def test_enable_preserves_unrelated_keys_and_existing_options(tmp_path: Path) -> None:
    _write(tmp_path, 'other: value\nfree:\n  branch: keep-me\n  zip: true\n')

    enable_free(tmp_path)

    document = _read(tmp_path)
    assert document['other'] == 'value'
    assert document['free'] == {'branch': 'keep-me', 'zip': True}


def test_enable_overrides_only_supplied_options(tmp_path: Path) -> None:
    _write(tmp_path, 'free:\n  branch: keep-me\n  zip: true\n')

    enable_free(tmp_path, zip_enabled=False)

    assert _read(tmp_path)['free'] == {'branch': 'keep-me', 'zip': False}


def test_enable_twice_is_idempotent(tmp_path: Path) -> None:
    enable_free(tmp_path)
    path = tmp_path / '.topdata' / 'build.yaml'
    first_bytes = path.read_bytes()
    first_mtime = path.stat().st_mtime_ns

    enable_free(tmp_path)

    assert path.read_bytes() == first_bytes
    assert path.stat().st_mtime_ns == first_mtime


def test_enable_with_invalid_branch_creates_nothing(tmp_path: Path) -> None:
    with pytest.raises(FreeManifestError, match='free.branch'):
        enable_free(tmp_path, branch='bad~branch')

    assert not (tmp_path / '.topdata').exists()


def test_enable_on_invalid_manifest_does_not_rewrite(tmp_path: Path) -> None:
    path = _write(tmp_path, 'free: [unclosed\n')
    original = path.read_bytes()

    with pytest.raises(FreeManifestError, match='Invalid YAML'):
        enable_free(tmp_path)

    assert path.read_bytes() == original


# ---------------------------------------------------------------------------
# disable
# ---------------------------------------------------------------------------


def test_disable_removes_free_key_but_keeps_other_keys(tmp_path: Path) -> None:
    _write(tmp_path, 'other: value\nfree:\n  branch: main-free\n')

    manifest = disable_free(tmp_path)

    assert _read(tmp_path) == {'other': 'value'}
    assert manifest.enabled is False
    assert manifest.path is not None


def test_disable_removes_file_and_empty_directory(tmp_path: Path) -> None:
    _write(tmp_path, 'free: {}\n')

    manifest = disable_free(tmp_path)

    assert not (tmp_path / '.topdata' / 'build.yaml').exists()
    assert not (tmp_path / '.topdata').exists()
    assert manifest.enabled is False
    assert manifest.path is None


def test_disable_is_noop_when_file_is_absent(tmp_path: Path) -> None:
    manifest = disable_free(tmp_path)

    assert not (tmp_path / '.topdata').exists()
    assert manifest.enabled is False


def test_disable_is_noop_when_key_is_absent(tmp_path: Path) -> None:
    path = _write(tmp_path, 'other: value\n')

    manifest = disable_free(tmp_path)

    assert path.is_file()
    assert _read(tmp_path) == {'other': 'value'}
    assert manifest.enabled is False


def test_disable_on_invalid_manifest_does_not_modify(tmp_path: Path) -> None:
    path = _write(tmp_path, 'free: [unclosed\n')
    original = path.read_bytes()

    with pytest.raises(FreeManifestError, match='Invalid YAML'):
        disable_free(tmp_path)

    assert path.read_bytes() == original


def test_disable_then_load_reports_disabled(tmp_path: Path) -> None:
    enable_free(tmp_path)

    disable_free(tmp_path)

    assert load_free_manifest(tmp_path).enabled is False
