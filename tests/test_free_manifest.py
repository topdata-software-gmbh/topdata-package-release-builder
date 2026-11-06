"""Tests for ``.topdata/build.yaml`` parsing and validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from topdata_package_release_builder.free_manifest import (
    DEFAULT_BRANCH,
    FreeManifestError,
    load_free_manifest,
)


def _write(plugin_root: Path, content: str) -> Path:
    path = plugin_root / '.topdata' / 'build.yaml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


# ---------------------------------------------------------------------------
# Enablement
# ---------------------------------------------------------------------------


def test_missing_file_is_disabled(tmp_path: Path) -> None:
    manifest = load_free_manifest(tmp_path)

    assert manifest.enabled is False
    assert manifest.path is None
    assert manifest.branch == DEFAULT_BRANCH
    assert manifest.zip is False


def test_empty_document_is_disabled(tmp_path: Path) -> None:
    _write(tmp_path, '')

    assert load_free_manifest(tmp_path).enabled is False


def test_comments_only_document_is_disabled(tmp_path: Path) -> None:
    _write(tmp_path, '# nothing here\n')

    assert load_free_manifest(tmp_path).enabled is False


def test_missing_free_key_is_disabled(tmp_path: Path) -> None:
    _write(tmp_path, 'other:\n  value: 1\n')

    assert load_free_manifest(tmp_path).enabled is False


@pytest.mark.parametrize('content', ['free:\n', 'free: {}\n', 'free: null\n'])
def test_empty_free_mapping_enables_defaults(tmp_path: Path, content: str) -> None:
    _write(tmp_path, content)

    manifest = load_free_manifest(tmp_path)

    assert manifest.enabled is True
    assert manifest.branch == 'main-free'
    assert manifest.zip is False


def test_custom_branch_and_zip(tmp_path: Path) -> None:
    _write(tmp_path, 'free:\n  branch: free-latest\n  zip: true\n')

    manifest = load_free_manifest(tmp_path)

    assert manifest.enabled is True
    assert manifest.branch == 'free-latest'
    assert manifest.zip is True


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path, 'free:\n  branch: main-free\n  future: yes\nother: 1\n')

    assert load_free_manifest(tmp_path).enabled is True


def test_manifest_path_is_reported(tmp_path: Path) -> None:
    path = _write(tmp_path, 'free: {}\n')

    assert load_free_manifest(tmp_path).path == path


# ---------------------------------------------------------------------------
# zip validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('value', ['1', '0', '"true"', '[]', '{}', 'null'])
def test_non_boolean_zip_aborts(tmp_path: Path, value: str) -> None:
    _write(tmp_path, f'free:\n  zip: {value}\n')

    with pytest.raises(FreeManifestError, match='free.zip'):
        load_free_manifest(tmp_path)


# ---------------------------------------------------------------------------
# Invalid documents
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'content',
    [
        '- one\n- two\n',
        'just a string\n',
        '42\n',
        'true\n',
    ],
)
def test_non_mapping_root_aborts(tmp_path: Path, content: str) -> None:
    _write(tmp_path, content)

    with pytest.raises(FreeManifestError, match='root document'):
        load_free_manifest(tmp_path)


@pytest.mark.parametrize(
    'content',
    [
        'free: []\n',
        'free:\n  - a\n  - b\n',
        'free: "text"\n',
        'free: 1\n',
        'free: true\n',
    ],
)
def test_non_mapping_free_aborts(tmp_path: Path, content: str) -> None:
    _write(tmp_path, content)

    with pytest.raises(FreeManifestError, match="'free' must be a mapping"):
        load_free_manifest(tmp_path)


def test_invalid_yaml_aborts(tmp_path: Path) -> None:
    _write(tmp_path, 'free: [unclosed\n')

    with pytest.raises(FreeManifestError, match='Invalid YAML'):
        load_free_manifest(tmp_path)


# ---------------------------------------------------------------------------
# Branch validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'branch',
    [
        123,
        True,
        '[]',
    ],
)
def test_non_string_branch_aborts(tmp_path: Path, branch) -> None:
    _write(tmp_path, f'free:\n  branch: {branch}\n')

    with pytest.raises(FreeManifestError, match='expected a string'):
        load_free_manifest(tmp_path)


@pytest.mark.parametrize(
    'branch',
    [
        "''",
        "' padded'",
        "'padded '",
        "'has space'",
        "'has\\ttab'",
        "'a..b'",
        "'bad~branch'",
        "'double//slash'",
        "'branch.lock'",
    ],
)
def test_invalid_branch_aborts(tmp_path: Path, branch: str) -> None:
    _write(tmp_path, f'free:\n  branch: {branch}\n')

    with pytest.raises(FreeManifestError, match='free.branch'):
        load_free_manifest(tmp_path)


def test_valid_branch_with_slash_is_accepted(tmp_path: Path) -> None:
    _write(tmp_path, 'free:\n  branch: feature/free\n')

    assert load_free_manifest(tmp_path).branch == 'feature/free'
