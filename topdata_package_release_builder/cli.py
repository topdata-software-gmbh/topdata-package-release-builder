#!/usr/bin/env python3
"""Command line interface for the Shopware Plugin Builder."""
import os
from pathlib import Path
import tempfile
from rich.console import Console
from rich.panel import Panel
import click

from .config import load_env, get_remote_config
from .git import get_git_info
from .plugin import get_plugin_info, copy_plugin_files, create_archive
from .release import create_release_info
from .remote import sync_to_remote

console = Console()

@click.command()
@click.option('--output-dir', default='./builds', help='Local directory for built archives')
@click.option('--no-sync', is_flag=True, help='Disable syncing to remote server')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def build_plugin(output_dir, no_sync, verbose):
    """Build and package Shopware 6 plugin for release."""
    # Load environment variables
    load_env(verbose=verbose, console=console)
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        if verbose:
            console.print(f"[dim]→ Created output directory: {output_dir}[/]")

        # Check if builds/ is in .gitignore
        gitignore_path = Path('.gitignore')
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                if 'builds/' not in f.read():
                    console.print("[yellow]Warning:[/] The 'builds/' directory is not in .gitignore. "
                                "It's recommended to add it to prevent committing built packages.")

        with console.status("[bold green]Building plugin...") as status:
            # Get information
            status.update("[bold blue]Getting git information...")
            branch, commit = get_git_info(verbose=verbose, console=console)

            status.update("[bold blue]Reading plugin information...")
            plugin_name, version = get_plugin_info(verbose=verbose, console=console)

            # Build process
            with tempfile.TemporaryDirectory() as temp_dir:
                status.update("[bold blue]Copying plugin files...")
                if verbose:
                    console.print(f"[dim]→ Using temporary directory: {temp_dir}[/]")
                plugin_dir = copy_plugin_files(temp_dir, plugin_name, verbose=verbose, console=console)

                status.update("[bold blue]Creating release info...")
                release_info = create_release_info(plugin_name, branch, commit, version, verbose=verbose, console=console)
                print(release_info)
                with open(os.path.join(plugin_dir, 'release_info.txt'), 'w') as f:
                    f.write(str(release_info))

                status.update("[bold blue]Creating ZIP archive...")
                zip_name = f"{plugin_name}-v{version}.zip"
                zip_path = os.path.join(output_dir, zip_name)
                create_archive(output_dir, plugin_name, version, temp_dir)

                # Get remote config and sync if enabled
                sync_status = None
                remote_config = get_remote_config(plugin_name, verbose=verbose, console=console)
                if remote_config:
                    if no_sync:
                        sync_status = False
                        console.print("[yellow]Remote sync is disabled by --no-sync flag[/]")
                    else:
                        status.update("[bold blue]Syncing to remote server...")
                        sync_path = sync_to_remote(zip_path, remote_config, verbose=verbose, console=console)
                        sync_status = sync_path

        _show_success_message(plugin_name, version, zip_name, output_dir, sync_status)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}", style="red")
        raise click.Abort()

def _show_success_message(plugin_name, version, zip_name, output_dir, sync_status=None):
    """Display success message after build completion."""
    sync_message = ""
    if sync_status is False:
        sync_message = "\n[yellow]Remote sync was disabled[/]"
    elif sync_status:
        sync_message = f"\n[green]Successfully synced to remote server: {sync_status}[/]"

    console.print(Panel(f"""
[bold green]Plugin successfully built![/]
Plugin: {plugin_name}
Version: v{version}
Archive: {zip_name}
Location: {output_dir}/{zip_name}{sync_message}

[italic]Note: Built packages are stored in the 'builds/' directory.[/]
    """, title="Success"))

def main():
    """Entry point for the CLI."""
    build_plugin()

if __name__ == '__main__':
    main()
