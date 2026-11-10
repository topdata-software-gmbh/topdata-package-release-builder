"""``sw-build self-upgrade``: pull the latest tool code and refresh dependencies."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from ..config import PROJECT_ROOT

console = Console()

_STASH_MESSAGE = 'sw-build self-upgrade'


def _run_git(*args: str, project_root: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command in the tool checkout and capture its output."""
    return subprocess.run(
        ['git', *args],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_git_repo(project_root: Path) -> None:
    """Abort unless the installation is a Git checkout that can be pulled."""
    if not (project_root / '.git').exists():
        raise click.ClickException(
            'This installation is not a Git repository. Cannot self-upgrade.'
        )


def _check_local_changes(project_root: Path, force: bool) -> bool:
    """Return True when local changes were stashed, raise when they block the upgrade."""
    status = _run_git('status', '--porcelain', project_root=project_root)
    if status.returncode != 0:
        raise click.ClickException(
            f'Failed to check git status: {status.stderr.strip() or status.stdout.strip()}'
        )

    if not status.stdout.strip():
        return False

    if not force:
        raise click.ClickException(
            'You have uncommitted local changes. Commit, stash or revert them before '
            'upgrading, or rerun with --force to stash them automatically.'
        )

    console.print('[yellow]Local changes detected. Stashing them (--force used)...[/]')
    stash = _run_git(
        'stash', 'push', '--include-untracked', '-m', _STASH_MESSAGE, project_root=project_root
    )
    if stash.returncode != 0:
        raise click.ClickException(
            f'git stash failed: {stash.stderr.strip() or stash.stdout.strip()}'
        )
    if stash.stdout.strip():
        console.print(f'[dim]{stash.stdout.strip()}[/]')
    return True


def _pull_latest(project_root: Path) -> bool:
    """Pull the tracked branch; return False when the checkout was already current."""
    console.print('[blue]Pulling latest changes from Git...[/]')
    result = _run_git('pull', project_root=project_root)
    if result.returncode != 0:
        raise click.ClickException(
            f'git pull failed:\n{result.stderr.strip() or result.stdout.strip()}'
        )

    if 'Already up to date' in result.stdout:
        console.print('[green]Tool is already up to date.[/]')
        return False

    if result.stdout.strip():
        console.print(f'[dim]{result.stdout.strip()}[/]')
    return True


def _dependency_command(project_root: Path) -> list[str]:
    """Reinstall into the interpreter that is running this command.

    ``scripts/install.sh`` installs the package into the repository's ``.venv``
    and links its launcher onto PATH, so the refresh must target
    ``sys.executable`` instead of whichever environment happens to be active.
    """
    target = str(Path(sys.executable))
    if shutil.which('uv'):
        console.print("[dim]Using 'uv' for fast installation...[/]")
        return ['uv', 'pip', 'install', '--python', target, '-e', str(project_root)]
    console.print("[dim]Using 'pip' for installation...[/]")
    return [target, '-m', 'pip', 'install', '-e', str(project_root)]


def _refresh_dependencies(project_root: Path) -> None:
    """Reinstall the package in editable mode so new dependencies are picked up."""
    console.print('[blue]Refreshing dependencies...[/]')
    result = subprocess.run(
        _dependency_command(project_root), cwd=str(project_root), check=False
    )
    if result.returncode != 0:
        raise click.ClickException(
            'Failed to refresh dependencies. Run the install command manually in '
            f'{project_root}.'
        )


def _self_upgrade(project_root: Path, force: bool) -> None:
    """Pull the latest code and refresh dependencies when the checkout advanced."""
    _ensure_git_repo(project_root)
    console.print(f'[blue]Checking for updates in {project_root}...[/]')
    _check_local_changes(project_root, force)

    if not _pull_latest(project_root):
        return

    _refresh_dependencies(project_root)
    console.print(
        '[bold green]Upgrade complete! Please re-run your command.[/]'
    )


@click.command('self-upgrade')
@click.option(
    '--force',
    '-f',
    is_flag=True,
    help='Stash local changes (including untracked files) before upgrading.',
)
def self_upgrade_command(force: bool) -> None:
    """Pull the latest sw-build code from Git and refresh dependencies."""
    _self_upgrade(Path(PROJECT_ROOT), force)
