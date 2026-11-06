"""CLI-level tests for free branch wiring, ordering, skip and archive behavior."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

import topdata_package_release_builder.cli as cli
from topdata_package_release_builder.free_branch import FreePublishError


def _isolate_env(monkeypatch, release_dir: Path, *, remote: bool = False) -> None:
    monkeypatch.setenv('RELEASE_DIR', str(release_dir))
    monkeypatch.setenv('MANUALS_DIR', '')
    monkeypatch.setenv('DOCS_GENERATOR_PROJECT_PATH', '')
    monkeypatch.setenv('DOWNLOAD_BASE_URL', 'https://downloads.example.com')
    monkeypatch.setenv('SLACK_WEBHOOK_URL', 'https://hooks.example.com/services/x')
    monkeypatch.setenv('FOUNDATION_PLUGIN_PATH', '')
    if remote:
        monkeypatch.setenv('RSYNC_SSH_HOST', 'user@example.com')
        monkeypatch.setenv('RSYNC_SSH_PORT', '22')
        monkeypatch.setenv('RSYNC_REMOTE_PATH_RELEASES_FOLDER', '/var/releases/')
    else:
        monkeypatch.setenv('RSYNC_SSH_HOST', '')
        monkeypatch.setenv('RSYNC_REMOTE_PATH_RELEASES_FOLDER', '')


def _invoke(repo, release_dir: Path, *extra: str):
    return CliRunner().invoke(
        cli.build_plugin,
        [
            '--source-dir',
            str(repo['root']),
            '--output-dir',
            str(release_dir),
            '--version-increment',
            'none',
            *extra,
        ],
    )


def _commit_manifest(repo, git, content: str) -> None:
    path = repo['root'] / '.topdata' / 'build.yaml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    git('add', '-A', cwd=repo['root'])
    git('commit', '-m', 'add free manifest', cwd=repo['root'])


def _no_prompt(monkeypatch) -> None:
    class _Answer:
        def execute(self) -> bool:
            return False

    monkeypatch.setattr(cli.inquirer, 'confirm', lambda **kwargs: _Answer())


def _fake_sync(zip_path, remote_config, verbose=False, console=None):
    name = os.path.basename(zip_path)
    return f'user@example.com:/var/releases/topdata-demo-sw6/{name}'


# ---------------------------------------------------------------------------
# No-manifest regression
# ---------------------------------------------------------------------------


def test_no_manifest_regression(plugin_repo, tmp_path, monkeypatch, git) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release)
    monkeypatch.setattr(
        cli, 'publish_free_branch', lambda **kwargs: pytest.fail('free publish must not run')
    )

    result = _invoke(plugin_repo, release)

    assert result.exit_code == 0, result.output
    assert git(
        'ls-remote', '--heads', 'origin', 'refs/heads/main-free', cwd=plugin_repo['root']
    ).strip() == ''
    names = {path.name for path in release.iterdir()}
    assert 'TopdataDemoSW6-v1.4.0.zip' in names
    assert not any(name.startswith('Free') for name in names)


# ---------------------------------------------------------------------------
# Automatic publication
# ---------------------------------------------------------------------------


def test_manifest_publishes_free_branch(plugin_repo, tmp_path, monkeypatch, git) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release)
    _commit_manifest(plugin_repo, git, 'free: {}\n')

    result = _invoke(plugin_repo, release)

    assert result.exit_code == 0, result.output
    assert git(
        'rev-list', '--count', 'main-free', cwd=plugin_repo['origin']
    ).strip() == '1'
    assert 'composer.json' in git('ls-tree', '--name-only', 'main-free', cwd=plugin_repo['origin'])
    names = {path.name for path in release.iterdir()}
    assert not any(name.startswith('Free') for name in names)
    assert git('status', '--porcelain', cwd=plugin_repo['root']) == ''


def test_unchanged_content_does_not_add_commit(plugin_repo, tmp_path, monkeypatch, git) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release)
    _commit_manifest(plugin_repo, git, 'free: {}\n')

    assert _invoke(plugin_repo, release).exit_code == 0
    first_tip = git('rev-parse', 'main-free', cwd=plugin_repo['origin']).strip()
    assert _invoke(plugin_repo, release).exit_code == 0

    assert git('rev-parse', 'main-free', cwd=plugin_repo['origin']).strip() == first_tip
    assert git('rev-list', '--count', 'main-free', cwd=plugin_repo['origin']).strip() == '1'


# ---------------------------------------------------------------------------
# Optional free archive
# ---------------------------------------------------------------------------


def test_zip_false_creates_no_archive_or_free_notification(
    plugin_repo, tmp_path, monkeypatch, git
) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release, remote=True)
    _commit_manifest(plugin_repo, git, 'free:\n  zip: false\n')

    notifications = []
    syncs = []

    def _sync(zip_path, remote_config, verbose=False, console=None):
        syncs.append(os.path.basename(zip_path))
        return _fake_sync(zip_path, remote_config, verbose, console)

    monkeypatch.setattr(cli, 'sync_to_remote', _sync)
    monkeypatch.setattr(
        cli,
        'send_release_notification',
        lambda **kwargs: notifications.append(kwargs) or True,
    )

    result = _invoke(plugin_repo, release, '--notify-slack')

    assert result.exit_code == 0, result.output
    assert 'FreeTopdataDemoSW6-v1.4.0.zip' not in {path.name for path in release.iterdir()}
    assert all('Free' not in name for name in syncs)
    assert notifications and notifications[0]['free_info'] is None


def test_zip_true_creates_and_syncs_free_archive(
    plugin_repo, tmp_path, monkeypatch, git
) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release, remote=True)
    _commit_manifest(plugin_repo, git, 'free:\n  zip: true\n')

    notifications = []
    monkeypatch.setattr(cli, 'sync_to_remote', _fake_sync)
    monkeypatch.setattr(
        cli,
        'send_release_notification',
        lambda **kwargs: notifications.append(kwargs) or True,
    )

    result = _invoke(plugin_repo, release, '--notify-slack')

    assert result.exit_code == 0, result.output
    assert (release / 'FreeTopdataDemoSW6-v1.4.0.zip').is_file()
    assert notifications
    free_info = notifications[0]['free_info']
    assert free_info is not None
    assert free_info['name'] == 'FreeTopdataDemoSW6'
    assert free_info['zip_name'] == 'FreeTopdataDemoSW6-v1.4.0.zip'
    assert free_info['sync_status'] is True
    assert free_info['download_url'] is not None


def test_no_sync_keeps_free_archive_local_and_publishes_branch(
    plugin_repo, tmp_path, monkeypatch, git
) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release, remote=True)
    _commit_manifest(plugin_repo, git, 'free:\n  zip: true\n')

    syncs = []
    monkeypatch.setattr(
        cli, 'sync_to_remote', lambda *args, **kwargs: syncs.append(args) or 'unused'
    )

    result = _invoke(plugin_repo, release, '--no-sync')

    assert result.exit_code == 0, result.output
    assert (release / 'FreeTopdataDemoSW6-v1.4.0.zip').is_file()
    assert syncs == []
    assert git('rev-parse', 'main-free', cwd=plugin_repo['origin']).strip() != ''


# ---------------------------------------------------------------------------
# Safe failure and skip
# ---------------------------------------------------------------------------


def test_dirty_working_tree_aborts_before_paid_work(
    plugin_repo, tmp_path, monkeypatch, git
) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release, remote=True)
    _commit_manifest(plugin_repo, git, 'free: {}\n')
    _no_prompt(monkeypatch)

    uploads = []
    notifications = []
    monkeypatch.setattr(cli, 'sync_to_remote', lambda *a, **k: uploads.append(a) or 'x')
    monkeypatch.setattr(
        cli,
        'send_release_notification',
        lambda **kwargs: notifications.append(kwargs) or True,
    )
    (plugin_repo['root'] / 'README.md').write_text('# dirty\n')

    result = _invoke(plugin_repo, release, '--notify-slack')

    assert result.exit_code != 0
    assert uploads == []
    assert notifications == []
    assert not any(path.suffix == '.zip' for path in release.iterdir())


def test_invalid_manifest_aborts(plugin_repo, tmp_path, monkeypatch, git) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release, remote=True)
    _commit_manifest(plugin_repo, git, 'free: [unclosed\n')

    uploads = []
    monkeypatch.setattr(cli, 'sync_to_remote', lambda *a, **k: uploads.append(a) or 'x')

    result = _invoke(plugin_repo, release)

    assert result.exit_code != 0
    assert uploads == []
    assert not any(path.suffix == '.zip' for path in release.iterdir())


def test_missing_origin_aborts(plugin_repo, tmp_path, monkeypatch, git) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release, remote=True)
    _commit_manifest(plugin_repo, git, 'free: {}\n')
    git('remote', 'remove', 'origin', cwd=plugin_repo['root'])

    uploads = []
    monkeypatch.setattr(cli, 'sync_to_remote', lambda *a, **k: uploads.append(a) or 'x')

    result = _invoke(plugin_repo, release)

    assert result.exit_code != 0
    assert uploads == []
    assert not any(path.suffix == '.zip' for path in release.iterdir())


def test_rejected_push_aborts_before_paid_work(
    plugin_repo, tmp_path, monkeypatch, git
) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release, remote=True)
    _commit_manifest(plugin_repo, git, 'free: {}\n')

    uploads = []
    notifications = []
    monkeypatch.setattr(
        cli,
        'publish_free_branch',
        lambda **kwargs: (_ for _ in ()).throw(FreePublishError('push rejected')),
    )
    monkeypatch.setattr(cli, 'sync_to_remote', lambda *a, **k: uploads.append(a) or 'x')
    monkeypatch.setattr(
        cli,
        'send_release_notification',
        lambda **kwargs: notifications.append(kwargs) or True,
    )

    result = _invoke(plugin_repo, release, '--notify-slack')

    assert result.exit_code != 0
    assert uploads == []
    assert notifications == []
    assert not any(path.suffix == '.zip' for path in release.iterdir())


def test_skip_free_warns_and_lets_paid_release_proceed(
    plugin_repo, tmp_path, monkeypatch, git
) -> None:
    release = tmp_path / 'releases'
    _isolate_env(monkeypatch, release)
    _commit_manifest(plugin_repo, git, 'free: {}\n')
    monkeypatch.setattr(
        cli, 'publish_free_branch', lambda **kwargs: pytest.fail('free publish must not run')
    )

    result = _invoke(plugin_repo, release, '--skip-free')

    assert result.exit_code == 0, result.output
    assert 'skip' in result.output.lower()
    assert (release / 'TopdataDemoSW6-v1.4.0.zip').is_file()
    assert git(
        'ls-remote', '--heads', 'origin', 'refs/heads/main-free', cwd=plugin_repo['root']
    ).strip() == ''
