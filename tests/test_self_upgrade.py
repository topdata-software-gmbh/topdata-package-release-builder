"""Tests for ``sw-build self-upgrade`` against real temporary Git checkouts."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

import topdata_package_release_builder.cli as cli
from topdata_package_release_builder.commands import self_upgrade_cmd as upgrade


@pytest.fixture
def tool_checkout(tmp_path, git):
    """An editable-install checkout tracking a bare ``origin``."""
    origin = tmp_path / 'origin.git'
    origin.mkdir()
    git('init', '--bare', '-b', 'main', cwd=origin)

    root = tmp_path / 'tool'
    root.mkdir()
    git('init', '-b', 'main', cwd=root)
    git('config', 'user.name', 'Test', cwd=root)
    git('config', 'user.email', 'test@example.com', cwd=root)
    (root / 'pyproject.toml').write_text('[project]\nname = "tool"\n', encoding='utf-8')
    (root / 'README.md').write_text('# Tool\n', encoding='utf-8')
    git('add', '-A', cwd=root)
    git('commit', '-m', 'initial', cwd=root)
    git('remote', 'add', 'origin', str(origin), cwd=root)
    git('push', '-u', 'origin', 'main', cwd=root)

    return {'root': root, 'origin': origin}


@pytest.fixture
def upstream_commit(tmp_path, git):
    """Return a factory that pushes a new commit to the checkout's origin."""

    def _push(checkout: dict, filename: str = 'UPGRADE') -> None:
        clone = tmp_path / f'developer-{filename}'
        git('clone', str(checkout['origin']), str(clone), cwd=tmp_path)
        git('config', 'user.name', 'Test', cwd=clone)
        git('config', 'user.email', 'test@example.com', cwd=clone)
        (clone / filename).write_text('new\n', encoding='utf-8')
        git('add', '-A', cwd=clone)
        git('commit', '-m', f'add {filename}', cwd=clone)
        git('push', 'origin', 'main', cwd=clone)

    return _push


def _invoke(monkeypatch, checkout: Path, *args: str):
    monkeypatch.setattr(upgrade, 'PROJECT_ROOT', checkout)
    return CliRunner().invoke(cli.cli, ['self-upgrade', *args])


def test_rejects_non_git_installation(tmp_path: Path, monkeypatch) -> None:
    result = _invoke(monkeypatch, tmp_path)

    assert result.exit_code != 0
    assert 'not a Git repository' in result.output


def test_refuses_dirty_tree_without_force(tool_checkout, monkeypatch) -> None:
    root = tool_checkout['root']
    (root / 'README.md').write_text('# Dirty\n', encoding='utf-8')

    result = _invoke(monkeypatch, root)

    assert result.exit_code != 0
    assert 'uncommitted local changes' in result.output
    assert (root / 'README.md').read_text(encoding='utf-8') == '# Dirty\n'


def test_force_stashes_changes_and_pulls(tool_checkout, upstream_commit, monkeypatch, git) -> None:
    root = tool_checkout['root']
    (root / 'UNTRACKED').write_text('local\n', encoding='utf-8')
    upstream_commit(tool_checkout, filename='UPGRADE')
    refreshed = []
    monkeypatch.setattr(upgrade, '_refresh_dependencies', lambda path: refreshed.append(path))

    result = _invoke(monkeypatch, root, '--force')

    assert result.exit_code == 0, result.output
    assert 'Stashing them' in result.output
    assert not (root / 'UNTRACKED').exists()
    assert 'sw-build self-upgrade' in git('stash', 'list', cwd=root)
    assert (root / 'UPGRADE').is_file()
    assert refreshed == [root]


def test_already_up_to_date_skips_dependency_refresh(tool_checkout, monkeypatch) -> None:
    refreshed = []
    monkeypatch.setattr(upgrade, '_refresh_dependencies', lambda path: refreshed.append(path))

    result = _invoke(monkeypatch, tool_checkout['root'])

    assert result.exit_code == 0, result.output
    assert 'already up to date' in result.output
    assert refreshed == []


def test_pull_refreshes_dependencies(tool_checkout, upstream_commit, monkeypatch) -> None:
    refreshed = []
    monkeypatch.setattr(upgrade, '_refresh_dependencies', lambda path: refreshed.append(path))
    upstream_commit(tool_checkout)

    result = _invoke(monkeypatch, tool_checkout['root'])

    assert result.exit_code == 0, result.output
    assert (tool_checkout['root'] / 'UPGRADE').is_file()
    assert refreshed == [tool_checkout['root']]


def test_dependency_command_targets_running_interpreter(monkeypatch) -> None:
    project_root = Path('/tmp/tool')
    monkeypatch.setattr(upgrade.shutil, 'which', lambda name: '/usr/bin/uv')

    with_uv = upgrade._dependency_command(project_root)

    assert with_uv[:4] == ['uv', 'pip', 'install', '--python']
    assert with_uv[4] == str(Path(sys.executable))
    assert with_uv[-2:] == ['-e', str(project_root)]

    monkeypatch.setattr(upgrade.shutil, 'which', lambda name: None)
    without_uv = upgrade._dependency_command(project_root)

    assert without_uv[:3] == [str(Path(sys.executable)), '-m', 'pip']
    assert without_uv[-2:] == ['-e', str(project_root)]


def test_pull_failure_is_reported(tool_checkout, upstream_commit, monkeypatch) -> None:
    refreshed = []
    monkeypatch.setattr(upgrade, '_refresh_dependencies', lambda path: refreshed.append(path))
    upstream_commit(tool_checkout)
    tool_checkout['origin'].rename(tool_checkout['origin'].with_name('origin-gone'))

    result = _invoke(monkeypatch, tool_checkout['root'])

    assert result.exit_code != 0
    assert 'git pull failed' in result.output
    assert refreshed == []
