#!/usr/bin/env python3
"""Command line interface for the Shopware Plugin Builder."""
import os
from pathlib import Path
import tempfile
from rich.console import Console
from rich.panel import Panel
import click

from .git import get_git_info
from .plugin import get_plugin_info, copy_plugin_files, create_archive
from .release import create_release_info, sync_to_remote

console = Console()

@click.command()
@click.option('--remote-path', required=False, help='Remote path for rsync (user@host:/path)')
@click.option('--output-dir', default='./builds', help='Local directory for built archives')
def build_plugin(remote_path, output_dir):
    """Build and package Shopware 6 plugin for release."""
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        with console.status("[bold green]Building plugin...") as status:
            # Get information
            status.update("[bold blue]Getting git information...")
            branch, commit = get_git_info()

            status.update("[bold blue]Reading plugin information...")
            plugin_name, version = get_plugin_info()

            # Build process
            with tempfile.TemporaryDirectory() as temp_dir:
                status.update("[bold blue]Copying plugin files...")
                plugin_dir = copy_plugin_files(temp_dir, plugin_name)

                status.update("[bold blue]Creating release info...")
                release_info = create_release_info(plugin_name, branch, commit, version)
                print(release_info)
                with open(os.path.join(plugin_dir, 'release_info.txt'), 'w') as f:
                    f.write(str(release_info))

                status.update("[bold blue]Creating ZIP archive...")
                zip_name = f"{plugin_name}-v{version}.zip"
                zip_path = os.path.join(output_dir, zip_name)
                create_archive(output_dir, plugin_name, version, temp_dir)

                if remote_path:
                    status.update("[bold blue]Syncing to remote server...")
                    sync_to_remote(zip_path, remote_path)

        _show_success_message(plugin_name, version, zip_name, remote_path)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}", style="red")
        raise click.Abort()

def _show_success_message(plugin_name, version, zip_name, remote_path):
    """Display success message after build completion."""
    console.print(Panel(f"""
[bold green]Plugin successfully built and deployed![/]
Plugin: {plugin_name}
Version: v{version}
Archive: {zip_name}
Remote path: {remote_path if remote_path else 'Not provided'}
    """, title="Success"))

def main():
    """Entry point for the CLI."""
    build_plugin()

if __name__ == '__main__':
    main()
