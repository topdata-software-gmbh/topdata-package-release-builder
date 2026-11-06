"""Integration tests for free payload assembly and branch publication."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from topdata_package_release_builder import free_branch
from topdata_package_release_builder.free_branch import (
    FreePublishError,
    build_free_payload,
    publish_free_branch,
)
from topdata_package_release_builder.string_utils import camel_to_kebab_for_js_asset


def _build(repo, temp_dir, *, foundation=None):
    return build_free_payload(
        source_dir=repo['root'],
        plugin_name=repo['name'],
        version=repo['version'],
        branch='main',
        commit='abc1234',
        foundation_plugin_path=foundation,
        assets=None,
        console=None,
        temp_dir=temp_dir,
    )


def _publish(repo, payload_root, branch='main-free') -> free_branch.FreeSnapshot:
    return publish_free_branch(
        repo_root=repo['root'],
        payload_root=payload_root,
        branch=branch,
        version=repo['version'],
        console=None,
    )


def _remote_tip(git, origin: Path, branch: str = 'main-free') -> str:
    return git('rev-parse', f'refs/heads/{branch}', cwd=origin).strip()


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------


def test_build_payload_renames_and_places_plugin_at_root(plugin_repo, tmp_path: Path) -> None:
    free_name, payload_root = _build(plugin_repo, tmp_path / 'payload')

    assert free_name == 'FreeTopdataDemoSW6'
    assert payload_root.name == free_name
    assert (payload_root / 'composer.json').is_file()
    assert (payload_root / 'src' / f'{free_name}.php').is_file()
    assert (payload_root / 'release_info.txt').is_file()

    composer = json.loads((payload_root / 'composer.json').read_text())
    assert composer['extra']['shopware-plugin-class'] == 'Topdata\\FreeTopdataDemoSW6\\FreeTopdataDemoSW6'
    assert 'Topdata\\FreeTopdataDemoSW6\\' in composer['autoload']['psr-4']

    release_info = (payload_root / 'release_info.txt').read_text()
    assert 'FreeTopdataDemoSW6' in release_info
    assert 'v1.4.0' in release_info


def test_build_payload_excludes_topdata_and_vcs(plugin_repo, tmp_path: Path) -> None:
    manifest = plugin_repo['root'] / '.topdata' / 'build.yaml'
    manifest.parent.mkdir(parents=True)
    manifest.write_text('free: {}\n')

    _, payload_root = _build(plugin_repo, tmp_path / 'payload')

    assert not (payload_root / '.topdata').exists()
    assert not (payload_root / '.git').exists()


def test_build_payload_never_writes_source(plugin_repo, tmp_path: Path, git) -> None:
    before_status = git('status', '--porcelain', cwd=plugin_repo['root'])
    before_branch = git('rev-parse', '--abbrev-ref', 'HEAD', cwd=plugin_repo['root'])

    _build(plugin_repo, tmp_path / 'payload')

    assert git('status', '--porcelain', cwd=plugin_repo['root']) == before_status
    assert git('rev-parse', '--abbrev-ref', 'HEAD', cwd=plugin_repo['root']) == before_branch
    assert not (plugin_repo['root'] / 'release_info.txt').exists()


def test_rename_covers_storefront_asset_paths(plugin_repo, tmp_path: Path) -> None:
    asset_root = (
        plugin_repo['root']
        / 'src' / 'Resources' / 'app' / 'storefront' / 'dist' / 'storefront' / 'js'
        / 'topdata-demo-s-w6'
    )
    asset_root.mkdir(parents=True)
    (asset_root / 'topdata-demo-s-w6.js').write_text('console.log("demo");\n')

    free_name, payload_root = _build(plugin_repo, tmp_path / 'payload')
    free_kebab = camel_to_kebab_for_js_asset(free_name)

    renamed = (
        payload_root
        / 'src' / 'Resources' / 'app' / 'storefront' / 'dist' / 'storefront' / 'js'
        / free_kebab
    )
    assert renamed.is_dir()
    assert (renamed / f'{free_kebab}.js').is_file()


# ---------------------------------------------------------------------------
# Publication history
# ---------------------------------------------------------------------------


def test_first_publication_creates_parentless_snapshot(plugin_repo, tmp_path, git) -> None:
    _, payload_root = _build(plugin_repo, tmp_path / 'payload')
    snapshot = _publish(plugin_repo, payload_root)

    assert snapshot.committed is True
    assert snapshot.pushed is True
    assert snapshot.previous_tip is None

    origin = plugin_repo['origin']
    tip = _remote_tip(git, origin)
    assert tip == snapshot.commit
    assert git('rev-list', '--count', 'main-free', cwd=origin).strip() == '1'
    assert git('rev-list', '--parents', '-n', '1', 'main-free', cwd=origin).strip() == tip
    assert json.loads(git('show', 'main-free:composer.json', cwd=origin))['name'] == 'topdata/free-topdata-demo-sw6'
    assert 'FreeTopdataDemoSW6' in git('show', 'main-free:release_info.txt', cwd=origin)
    assert 'v1.4.0' in git('show', 'main-free:release_info.txt', cwd=origin)
    assert git('tag', cwd=origin).strip() == ''


def test_publication_leaves_checkout_untouched(plugin_repo, tmp_path, git) -> None:
    _, payload_root = _build(plugin_repo, tmp_path / 'payload')
    _publish(plugin_repo, payload_root)

    root = plugin_repo['root']
    assert git('status', '--porcelain', cwd=root) == ''
    assert git('rev-parse', '--abbrev-ref', 'HEAD', cwd=root).strip() == 'main'
    assert git('branch', '--list', 'main-free', cwd=root).strip() == ''


def test_second_publication_appends_to_remote_tip(plugin_repo, tmp_path, git) -> None:
    _, first_payload = _build(plugin_repo, tmp_path / 'payload-1')
    first = _publish(plugin_repo, first_payload)

    (plugin_repo['root'] / 'README.md').write_text('# Demo v2\n')
    git('add', '-A', cwd=plugin_repo['root'])
    git('commit', '-m', 'change', cwd=plugin_repo['root'])

    _, second_payload = _build(plugin_repo, tmp_path / 'payload-2')
    second = _publish(plugin_repo, second_payload)

    assert second.committed is True
    assert second.previous_tip == first.commit
    tip = _remote_tip(git, plugin_repo['origin'])
    assert tip == second.commit
    parent = git('rev-list', '--parents', '-n', '1', 'main-free', cwd=plugin_repo['origin']).split()
    assert parent == [second.commit, first.commit]
    assert git('rev-list', '--count', 'main-free', cwd=plugin_repo['origin']).strip() == '2'
    assert f'v{plugin_repo["version"]}' in git(
        'log', '-1', '--format=%s', 'main-free', cwd=plugin_repo['origin']
    )


def test_shop_clone_fast_forwards_with_git_pull(plugin_repo, tmp_path, git) -> None:
    _, first_payload = _build(plugin_repo, tmp_path / 'payload-1')
    _publish(plugin_repo, first_payload)

    shop = tmp_path / 'shop'
    git('clone', str(plugin_repo['origin']), str(shop), cwd=tmp_path)
    git('checkout', 'main-free', cwd=shop)

    for index in (2, 3):
        (plugin_repo['root'] / 'README.md').write_text(f'# Demo v{index}\n')
        git('add', '-A', cwd=plugin_repo['root'])
        git('commit', '-m', f'change {index}', cwd=plugin_repo['root'])
        _, payload = _build(plugin_repo, tmp_path / f'payload-{index}')
        _publish(plugin_repo, payload)

        git('pull', cwd=shop)
        assert (shop / 'composer.json').is_file()
        assert f'v{plugin_repo["version"]}' in (shop / 'release_info.txt').read_text()


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


def test_unchanged_payload_is_a_noop(plugin_repo, tmp_path, git) -> None:
    _, first_payload = _build(plugin_repo, tmp_path / 'payload-1')
    first = _publish(plugin_repo, first_payload)

    _, second_payload = _build(plugin_repo, tmp_path / 'payload-2')
    second = _publish(plugin_repo, second_payload)

    assert second.committed is False
    assert second.pushed is False
    assert second.commit is None
    assert second.timestamp_only is False
    assert _remote_tip(git, plugin_repo['origin']) == first.commit
    assert git('rev-list', '--count', 'main-free', cwd=plugin_repo['origin']).strip() == '1'


def test_timestamp_only_change_is_a_noop(plugin_repo, tmp_path, git) -> None:
    _, first_payload = _build(plugin_repo, tmp_path / 'payload-1')
    first = _publish(plugin_repo, first_payload)

    _, second_payload = _build(plugin_repo, tmp_path / 'payload-2')
    release_info = second_payload / 'release_info.txt'
    text = release_info.read_text()
    new_text = re.sub(
        r'(Created\s*│\s*)[^\s│]+\s+[^\s│]+',
        r'\g<1>1999-01-01 00:00',
        text,
    )
    assert new_text != text
    release_info.write_text(new_text)

    second = _publish(plugin_repo, second_payload)

    assert second.committed is False
    assert second.pushed is False
    assert second.timestamp_only is True
    assert _remote_tip(git, plugin_repo['origin']) == first.commit


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_missing_origin_aborts(plugin_repo, tmp_path, git) -> None:
    git('remote', 'remove', 'origin', cwd=plugin_repo['root'])
    _, payload_root = _build(plugin_repo, tmp_path / 'payload')

    with pytest.raises(FreePublishError, match='origin'):
        _publish(plugin_repo, payload_root)


def test_unreachable_origin_aborts(plugin_repo, tmp_path, git) -> None:
    git('remote', 'set-url', 'origin', str(tmp_path / 'does-not-exist.git'), cwd=plugin_repo['root'])
    _, payload_root = _build(plugin_repo, tmp_path / 'payload')

    with pytest.raises(FreePublishError):
        _publish(plugin_repo, payload_root)


def test_dirty_working_tree_aborts(plugin_repo, tmp_path, git) -> None:
    (plugin_repo['root'] / 'README.md').write_text('# uncommitted\n')
    _, payload_root = _build(plugin_repo, tmp_path / 'payload')

    with pytest.raises(FreePublishError, match='clean'):
        _publish(plugin_repo, payload_root)

    assert git('branch', '--list', 'main-free', cwd=plugin_repo['origin']).strip() == ''


def test_push_rejected_when_remote_moves(plugin_repo, tmp_path, git, monkeypatch) -> None:
    _, first_payload = _build(plugin_repo, tmp_path / 'payload-1')
    first = _publish(plugin_repo, first_payload)

    (plugin_repo['root'] / 'README.md').write_text('# local change\n')
    git('add', '-A', cwd=plugin_repo['root'])
    git('commit', '-m', 'local change', cwd=plugin_repo['root'])
    _, second_payload = _build(plugin_repo, tmp_path / 'payload-2')

    other = tmp_path / 'other'
    git('clone', str(plugin_repo['origin']), str(other), cwd=tmp_path)
    git('checkout', 'main-free', cwd=other)
    (other / 'README.md').write_text('# remote race\n')
    git('add', '-A', cwd=other)
    git('commit', '-m', 'remote race', cwd=other)
    git('push', 'origin', 'main-free', cwd=other)
    raced_tip = _remote_tip(git, plugin_repo['origin'])

    # Simulate the tip moving after our existence check/fetch: publish still
    # bases the commit on the old tip and the push must be rejected.
    monkeypatch.setattr(free_branch, '_remote_tip', lambda repo_root, branch: first.commit)

    with pytest.raises(FreePublishError):
        _publish(plugin_repo, second_payload)

    assert _remote_tip(git, plugin_repo['origin']) == raced_tip
    assert first.commit in git('rev-list', 'main-free', cwd=plugin_repo['origin'])


# ---------------------------------------------------------------------------
# Foundation injection
# ---------------------------------------------------------------------------


def test_foundation_is_injected_when_required(foundation_plugin_repo, tmp_path: Path) -> None:
    free_name, payload_root = _build(
        foundation_plugin_repo,
        tmp_path / 'payload',
        foundation=foundation_plugin_repo['foundation'],
    )

    assert free_name == 'FreeTopdataDemoSW6'
    assert (payload_root / 'src' / 'Foundation' / 'Service' / 'Helper.php').is_file()
    assert (payload_root / 'src' / 'Foundation' / 'Util' / 'StringUtil.php').is_file()

    composer = json.loads((payload_root / 'composer.json').read_text())
    assert 'topdata/topdata-foundation-sw6' not in composer.get('require', {})
    assert 'Topdata\\FreeTopdataDemoSW6\\Foundation\\' in composer['autoload']['psr-4']

    helper = (payload_root / 'src' / 'Foundation' / 'Service' / 'Helper.php').read_text()
    assert 'Topdata\\FreeTopdataDemoSW6\\Foundation\\Service' in helper
    assert 'Topdata\\TopdataFoundationSW6' not in helper


def test_no_foundation_code_without_requirement(plugin_repo, tmp_path: Path) -> None:
    _, payload_root = _build(plugin_repo, tmp_path / 'payload', foundation=None)

    assert not (payload_root / 'src' / 'Foundation').exists()
    composer = json.loads((payload_root / 'composer.json').read_text())
    assert 'Topdata\\FreeTopdataDemoSW6\\Foundation\\' not in composer['autoload']['psr-4']
