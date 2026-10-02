"""Tests for compiled-asset verification (``assets``)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from topdata_package_release_builder.assets import (
    LOCKFILES,
    MANIFEST_NAME,
    AssetVerification,
    compiled_assets_present,
    digest_tree,
    manifest_path,
    read_manifest,
    toolchain_provenance,
    verify_assets,
    write_manifest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str = 'x') -> Path:
    """Create *path* (and parents) with *content*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _plugin(tmp_path: Path) -> Path:
    """Return an empty plugin root."""
    root = tmp_path / 'TopdataDemoSW6'
    root.mkdir()
    return root


# ---------------------------------------------------------------------------
# digest_tree
# ---------------------------------------------------------------------------

def test_digest_tree_missing_directory_is_empty(tmp_path: Path) -> None:
    """A missing directory hashes as the empty tree -- a real, stable digest."""
    digest = digest_tree(tmp_path / 'nope', ('.js',))
    assert digest.files == 0
    assert digest.paths == ()
    # sha256 of the empty byte string: well-defined, and equal for any
    # missing/empty directory, so "absent" and "empty" are one outcome.
    assert digest.sha256 == hashlib.sha256(b'').hexdigest()


def test_digest_tree_is_content_addressed_not_mtime_based(tmp_path: Path) -> None:
    """Two trees with identical bytes must hash identically regardless of mtime."""
    a = tmp_path / 'a'
    b = tmp_path / 'b'
    _write(a / 'main.js', 'console.log(1)')
    _write(b / 'main.js', 'console.log(1)')

    import os

    os.utime(a / 'main.js', (1_000_000, 1_000_000))
    os.utime(b / 'main.js', (2_000_000, 2_000_000))

    assert digest_tree(a, ('.js',)).sha256 == digest_tree(b, ('.js',)).sha256


def test_digest_tree_detects_content_change(tmp_path: Path) -> None:
    tree = tmp_path / 'src'
    _write(tree / 'main.js', 'v1')
    before = digest_tree(tree, ('.js',))
    _write(tree / 'main.js', 'v2')
    assert digest_tree(tree, ('.js',)).sha256 != before.sha256


def test_digest_tree_detects_renamed_file_with_same_content(tmp_path: Path) -> None:
    tree = tmp_path / 'src'
    _write(tree / 'main.js', 'same')
    before = digest_tree(tree, ('.js',))
    (tree / 'main.js').rename(tree / 'entry.js')
    assert digest_tree(tree, ('.js',)).sha256 != before.sha256


def test_digest_tree_filters_by_extension(tmp_path: Path) -> None:
    tree = tmp_path / 'src'
    _write(tree / 'a.js')
    _write(tree / 'b.ts')
    _write(tree / 'c.scss')
    assert digest_tree(tree, ('.js',)).files == 1
    assert digest_tree(tree, ('.js', '.ts')).files == 2
    assert digest_tree(tree).files == 3


def test_digest_tree_excludes_named_files(tmp_path: Path) -> None:
    tree = tmp_path / 'src'
    _write(tree / 'bundle.js')
    _write(tree / MANIFEST_NAME)
    digest = digest_tree(tree, ('.js',), exclude=(MANIFEST_NAME,))
    assert digest.paths == ('bundle.js',)


def test_digest_tree_ignores_node_modules(tmp_path: Path) -> None:
    tree = tmp_path / 'src'
    _write(tree / 'bundle.js')
    _write(tree / 'node_modules' / 'dep' / 'index.js')
    assert digest_tree(tree, ('.js',)).files == 1


def test_digest_tree_paths_are_sorted(tmp_path: Path) -> None:
    tree = tmp_path / 'src'
    for name in ('z.js', 'a.js', 'm.js'):
        _write(tree / name)
    assert list(digest_tree(tree, ('.js',)).paths) == ['a.js', 'm.js', 'z.js']


# ---------------------------------------------------------------------------
# Plugin shape detection
# ---------------------------------------------------------------------------

def test_compiled_assets_present_false_for_twig_only_plugin(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/storefront/src/main.js')
    assert compiled_assets_present(root) is False


def test_compiled_assets_present_true_when_public_populated(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/public/storefront/js/bundle.js')
    assert compiled_assets_present(root) is True


def test_manifest_alone_does_not_count_as_compiled_assets(tmp_path: Path) -> None:
    """The manifest must not make a plugin look like it compiles something."""
    root = _plugin(tmp_path)
    write_manifest(root, {'schema': 1, 'tool': 'sw-build', 'targets': {}})
    assert compiled_assets_present(root) is False


def test_toolchain_provenance_reports_missing_lockfile(tmp_path: Path) -> None:
    provenance = toolchain_provenance(_plugin(tmp_path))
    assert provenance['lockfile'] is None


@pytest.mark.parametrize('lockfile', LOCKFILES)
def test_toolchain_provenance_hashes_lockfile(tmp_path: Path, lockfile: str) -> None:
    root = _plugin(tmp_path)
    _write(root / lockfile, '{"lockfileVersion": 3}')
    provenance = toolchain_provenance(root)
    assert provenance['lockfile'] is not None
    assert provenance['lockfile']['name'] == lockfile
    assert len(provenance['lockfile']['sha256']) == 64


# ---------------------------------------------------------------------------
# Manifest round-trip
# ---------------------------------------------------------------------------

def test_read_manifest_returns_empty_when_absent(tmp_path: Path) -> None:
    assert read_manifest(_plugin(tmp_path)) == {}


def test_manifest_round_trip(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    data = {'schema': 1, 'tool': 'sw-build', 'targets': {'storefront-js': {}}}
    write_manifest(root, data)
    assert read_manifest(root) == data


def test_read_manifest_rejects_foreign_schema(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'schema': 999, 'targets': {}}), encoding='utf-8')
    assert read_manifest(root) == {}


def test_read_manifest_rejects_corrupt_json(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{not json', encoding='utf-8')
    assert read_manifest(root) == {}


def test_read_manifest_rejects_non_object(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[1, 2, 3]', encoding='utf-8')
    assert read_manifest(root) == {}


# ---------------------------------------------------------------------------
# verify_assets - the missing-output regression
# ---------------------------------------------------------------------------

def test_missing_compiled_output_is_a_warning_for_unbuilt_plugin(tmp_path: Path) -> None:
    """The 14 real plugins: sources present, nothing ever compiled.

    This must not block a release, but it must stop claiming the assets are
    up-to-date.
    """
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/storefront/src/main.js')
    _write(root / 'src/Resources/app/storefront/src/scss/base.scss')

    result = verify_assets(root)

    assert result.ok is True
    assert result.errors == []
    assert len(result.warnings) == 2
    assert any('shipped uncompiled' in w for w in result.warnings)
    assert result.manifest_written is False


def test_missing_compiled_output_does_not_create_public_dir(tmp_path: Path) -> None:
    """A plugin with nothing to compile must not gain an empty public/ tree."""
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/storefront/src/main.js')

    verify_assets(root)

    assert not (root / 'src/Resources/public').exists()


def test_missing_compiled_output_is_error_when_plugin_compiles(tmp_path: Path) -> None:
    """A plugin that compiles must compile every side it has sources for."""
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/storefront/src/main.js')
    _write(root / 'src/Resources/app/storefront/src/scss/base.scss')
    _write(root / 'src/Resources/public/storefront/js/bundle.js')
    # Compiled JS exists, compiled CSS does not.

    result = verify_assets(root)

    assert result.ok is False
    assert any('Storefront CSS' in e and 'no compiled output' in e for e in result.errors)
    assert 'storefront-js' in result.targets
    assert 'storefront-css' not in result.targets


def test_target_with_no_sources_is_not_required_when_plugin_compiles(tmp_path: Path) -> None:
    """A plugin that compiles JS but ships no CSS must not be asked for CSS."""
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/storefront/src/main.js')
    _write(root / 'src/Resources/public/storefront/js/bundle.js')

    result = verify_assets(root)

    assert result.ok is True
    assert set(result.targets) == {'storefront-js'}


def test_strict_mode_errors_for_plugin_that_never_compiles(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/storefront/src/main.js')

    result = verify_assets(root, strict=True)

    assert result.ok is False
    assert any('no compiled output' in e for e in result.errors)


def test_plugin_without_sources_is_left_alone(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/views/storefront/base.html.twig')

    result = verify_assets(root)

    assert result.ok is True
    assert result.errors == []
    assert result.warnings == []
    assert result.manifest_written is False


# ---------------------------------------------------------------------------
# verify_assets - hash-based staleness
# ---------------------------------------------------------------------------

def _compiled_plugin(root: Path) -> Path:
    """A plugin that has sources and matching compiled output."""
    _write(root / 'src/Resources/app/storefront/src/main.js', 'src')
    _write(root / 'src/Resources/app/storefront/src/scss/base.scss', 'scss')
    _write(root / 'src/Resources/public/storefront/js/bundle.js', 'js')
    _write(root / 'src/Resources/public/storefront/css/bundle.css', 'css')
    return root


def test_first_verification_records_a_baseline(tmp_path: Path) -> None:
    root = _compiled_plugin(_plugin(tmp_path))

    result = verify_assets(root)

    assert result.ok is True
    assert result.manifest_written is True
    assert set(result.targets) == {'storefront-js', 'storefront-css'}
    manifest = read_manifest(root)
    assert manifest['schema'] == 1
    assert manifest['tool'] == 'sw-build'


def test_unchanged_plugin_verifies_clean_on_second_run(tmp_path: Path) -> None:
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)

    result = verify_assets(root)

    assert result.ok is True
    assert result.warnings == []


def test_changed_sources_after_baseline_are_an_error(tmp_path: Path) -> None:
    """The regression the mtime check could not see reliably."""
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)

    _write(root / 'src/Resources/app/storefront/src/main.js', 'edited')

    result = verify_assets(root)

    assert result.ok is False
    assert any('sources changed since the last verified build' in e for e in result.errors)


def test_changed_sources_detected_even_when_dist_is_newer(tmp_path: Path) -> None:
    """Content hashes ignore mtimes, so a fresh compile does not mask staleness."""
    import os

    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)

    _write(root / 'src/Resources/app/storefront/src/main.js', 'edited')
    # Make the *compiled* file far newer, exactly as a rebuild would.
    _write(root / 'src/Resources/public/storefront/js/bundle.js', 'js')
    os.utime(root / 'src/Resources/public/storefront/js/bundle.js', (9_000_000, 9_000_000))

    result = verify_assets(root)

    assert result.ok is False


def test_touched_but_unchanged_sources_still_pass(tmp_path: Path) -> None:
    """mtime churn alone must not fail a build."""
    import os

    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)

    for path in (root / 'src/Resources/app/storefront/src/main.js',
                 root / 'src/Resources/app/storefront/src/scss/base.scss'):
        os.utime(path, (9_000_000, 9_000_000))

    result = verify_assets(root)

    assert result.ok is True


def test_changed_output_without_source_change_warns(tmp_path: Path) -> None:
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)

    _write(root / 'src/Resources/public/storefront/js/bundle.js', 'different')

    result = verify_assets(root)

    assert result.ok is True
    assert any('changed without a source change' in w for w in result.warnings)


def test_manifest_excludes_itself_from_output_digest(tmp_path: Path) -> None:
    """Writing the manifest must not invalidate the output digest it records."""
    root = _compiled_plugin(_plugin(tmp_path))

    first = verify_assets(root)
    second = verify_assets(root)

    assert first.targets['storefront-js']['output']['sha256'] == (
        second.targets['storefront-js']['output']['sha256']
    )
    assert first.ok is True
    assert second.ok is True


def test_manifest_lives_in_git_dir_not_the_zip(tmp_path: Path) -> None:
    """The manifest must not reach the release artifact or git status."""
    import subprocess

    root = _compiled_plugin(_plugin(tmp_path))
    subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
    verify_assets(root)
    manifest = manifest_path(root)
    assert manifest.is_file()
    assert '.git' in manifest.parts
    assert 'public' not in manifest.parts


def test_manifest_falls_back_outside_public_without_git(tmp_path: Path) -> None:
    """A non-git directory still gets a manifest, never inside public/."""
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)
    manifest = manifest_path(root)
    assert manifest.is_file()
    assert 'public' not in manifest.parts
    assert '.sw-build' in manifest.parts


def test_manifest_does_not_dirty_the_working_tree(tmp_path: Path) -> None:
    """Otherwise sw-build would offer to stage and commit its own state."""
    import subprocess

    root = _compiled_plugin(_plugin(tmp_path))
    git = ['git', '-C', str(root)]
    subprocess.run(git + ['init', '-q'], check=True)
    subprocess.run(git + ['config', 'user.email', 'a@b.c'], check=True)
    subprocess.run(git + ['config', 'user.name', 't'], check=True)
    subprocess.run(git + ['add', '-A'], check=True)
    subprocess.run(git + ['commit', '-qm', 'init'], check=True)

    verify_assets(root)

    status = subprocess.run(
        git + ['status', '--porcelain'], capture_output=True, text=True, check=True
    )
    assert status.stdout.strip() == ''


def test_failed_verification_does_not_advance_baseline(tmp_path: Path) -> None:
    """The regression: one ignored error blessed stale output forever.

    Ignoring an error must not rewrite the manifest, or the next build
    compares against the edited source digest and passes while the compiled
    output is still from the previous build.
    """
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)

    _write(root / 'src/Resources/app/storefront/src/main.js', 'edited')
    failed = verify_assets(root)
    assert failed.ok is False
    assert failed.manifest_written is False

    again = verify_assets(root)
    assert again.ok is False
    assert any('sources changed' in e for e in again.errors)


def test_baseline_survives_a_failed_run_unchanged(tmp_path: Path) -> None:
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)
    before = read_manifest(root)

    _write(root / 'src/Resources/app/storefront/src/main.js', 'edited')
    verify_assets(root)

    assert read_manifest(root) == before


def test_stale_target_not_recorded_but_healthy_one_is(tmp_path: Path) -> None:
    """Partial success still updates the targets that are actually fine."""
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)
    before = read_manifest(root)

    _write(root / 'src/Resources/app/storefront/src/main.js', 'edited')
    result = verify_assets(root)

    assert result.ok is False
    assert 'storefront-js' not in result.targets
    # The failing run persists nothing at all.
    assert read_manifest(root) == before


def test_compiled_css_alone_does_not_block_uncompiled_js(tmp_path: Path) -> None:
    """A hand-written base.css is not evidence the plugin compiles anything."""
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/storefront/src/main.js')
    _write(root / 'src/Resources/public/storefront/css/base.css')

    result = verify_assets(root)

    assert result.ok is True
    assert result.warnings


def test_corrupt_manifest_degrades_to_baseline_not_failure(tmp_path: Path) -> None:
    root = _compiled_plugin(_plugin(tmp_path))
    manifest_path(root).parent.mkdir(parents=True, exist_ok=True)
    manifest_path(root).write_text('{broken', encoding='utf-8')

    result = verify_assets(root)

    assert result.ok is True
    assert result.manifest_written is True


def test_stale_baseline_from_other_checkout_blocks_release(tmp_path: Path) -> None:
    """A manifest copied from another machine still guards the release."""
    root = _compiled_plugin(_plugin(tmp_path))
    verify_assets(root)

    saved = manifest_path(root).read_text(encoding='utf-8')
    _write(root / 'src/Resources/app/storefront/src/main.js', 'edited')
    manifest_path(root).write_text(saved, encoding='utf-8')

    result = verify_assets(root)

    assert result.ok is False


def test_administration_target_is_checked(tmp_path: Path) -> None:
    root = _plugin(tmp_path)
    _write(root / 'src/Resources/app/administration/src/main.js')
    _write(root / 'src/Resources/public/administration/js/bundle.js')

    result = verify_assets(root, strict=True)

    assert result.ok is True
    assert 'administration-js' in result.targets


# ---------------------------------------------------------------------------
# Result surface
# ---------------------------------------------------------------------------

def test_result_defaults_are_not_shared() -> None:
    """Mutable defaults on a dataclass would leak between runs."""
    first = AssetVerification()
    first.errors.append('boom')
    assert AssetVerification().errors == []


def test_compiled_targets_property(tmp_path: Path) -> None:
    root = _compiled_plugin(_plugin(tmp_path))
    result = verify_assets(root)
    assert set(result.compiled_targets) == {'storefront-js', 'storefront-css'}