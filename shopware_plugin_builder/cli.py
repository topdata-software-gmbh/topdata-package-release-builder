#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
from datetime import datetime
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import click
import pytz

console = Console()


def get_git_info():
    """Get current git branch and commit information."""
    branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    return branch, commit


def get_plugin_info():
    """Extract plugin information from composer.json."""
    with open('composer.json', 'r') as f:
        composer_data = json.load(f)

    # Extract plugin class name without namespace
    plugin_class = composer_data['extra']['shopware-plugin-class']
    plugin_name = plugin_class.split('\\')[-1]

    # Get version from composer.json
    version = composer_data['version']

    return plugin_name, version


def create_release_info(branch, commit, version):
    """Create release_info.txt with formatted content."""
    now = datetime.now(pytz.timezone('Europe/Berlin'))

    table = Table(show_header=False, show_lines=True)
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Branch", branch)
    table.add_row("Commit ID", commit)
    table.add_row("Version", f"v{version}")
    table.add_row("Created", now.isoformat())

    return table.get_string()


@click.command()
@click.option('--remote-path', required=True, help='Remote path for rsync (user@host:/path)')
@click.option('--output-dir', default='./builds', help='Local directory for built archives')
def build_plugin(remote_path, output_dir):
    """Build and package Shopware 6 plugin for release."""
    try:
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        with console.status("[bold green]Building plugin...") as status:
            # Get git information
            status.update("[bold blue]Getting git information...")
            branch, commit = get_git_info()

            # Get plugin information
            status.update("[bold blue]Reading plugin information...")
            plugin_name, version = get_plugin_info()

            # Create temporary directory for building
            with tempfile.TemporaryDirectory() as temp_dir:
                plugin_dir = os.path.join(temp_dir, plugin_name)

                # Copy plugin files
                status.update("[bold blue]Copying plugin files...")
                shutil.copytree('.', plugin_dir, ignore=shutil.ignore_patterns(
                    '.git*', 'builds', '__pycache__', '*.pyc', 'node_modules', 'tests'
                ))

                # Create release info
                status.update("[bold blue]Creating release info...")
                release_info = create_release_info(branch, commit, version)
                with open(os.path.join(plugin_dir, 'release_info.txt'), 'w') as f:
                    f.write(str(release_info))

                # Create zip file
                status.update("[bold blue]Creating ZIP archive...")
                zip_name = f"{plugin_name}-v{version}.zip"
                zip_path = os.path.join(output_dir, zip_name)
                shutil.make_archive(
                    os.path.join(output_dir, f"{plugin_name}-v{version}"),
                    'zip',
                    temp_dir
                )

                # Sync to remote server
                status.update("[bold blue]Syncing to remote server...")
                subprocess.run([
                    'rsync',
                    '-av',
                    '--progress',
                    zip_path,
                    remote_path
                ], check=True)

        # Show success message
        console.print(Panel(f"""
[bold green]Plugin successfully built and deployed![/]
Plugin: {plugin_name}
Version: v{version}
Archive: {zip_name}
Remote path: {remote_path}
        """, title="Success"))

    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}", style="red")
        raise click.Abort()


if __name__ == '__main__':
    build_plugin()