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
