#!/usr/bin/env python3
"""Command line interface for the Shopware Plugin Builder."""
import os
from pathlib import Path
import tempfile
from rich.console import Console
from rich.panel import Panel
import click
from InquirerPy import inquirer

from .config import load_env, get_remote_config, get_release_dir, get_manuals_dir
from .git import get_git_info
from .plugin import get_plugin_info, copy_plugin_files, create_archive
from .release import create_release_info
from .remote import sync_to_remote
from .slack import send_release_notification
from .version import VersionBump, bump_version, update_composer_version, get_major_version
from .manual import copy_manuals

console = Console()


def _get_download_url(zip_file_rsync_path: str) -> str|None:
    downloadBaseUrl = os.getenv('DOWNLOAD_BASE_URL')
    if not downloadBaseUrl:
        return None
    # example: IN: root@vps1.srv.topinfra.de:/srv/files-topinfra-de/vol/files/sw6-plugin-releases/TopdataDevelopmentHelperSW6/TopdataDevelopmentHelperSW6-v0.0.5.zip
    # example: OUT: https://files.topinfra.de/sw6-plugin-releases/TopdataDevelopmentHelperSW6/TopdataDevelopmentHelperSW6-v0.0.5.zip
    parts = zip_file_rsync_path.split(':')
    if len(parts) != 2:
        return None
    host, path = parts
    path_parts = path.split('/')
    # last 2 parts are the plugin name and the zip file
    plugin_name = path_parts[-2]
    zip_file = path_parts[-1]
    return f"{downloadBaseUrl}/{plugin_name}/{zip_file}"


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--output-dir', help='Override release directory (default: RELEASE_DIR from .env)')
@click.option('--no-sync', is_flag=True, help='Disable syncing to remote server')
@click.option('--notify-slack', '-s', is_flag=True, help='Send notification to Slack after successful upload')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def build_plugin(output_dir, no_sync, notify_slack, verbose):
    """Build and package Shopware 6 plugin for release."""
    # Load environment variables
    load_env(verbose=verbose, console=console)
    try:
        # Use RELEASE_DIR from .env if no output_dir specified
        if not output_dir:
            output_dir = get_release_dir(verbose=verbose, console=console)
            if not output_dir:
                raise click.UsageError("No output directory specified and RELEASE_DIR not set in .env")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        if verbose:
            console.print(f"[dim]→ Using release directory: {output_dir}[/]")

        with console.status("[bold green]Building plugin...") as status:
            # Get information
            status.update("[bold blue]Getting git information...")
            branch, commit = get_git_info(verbose=verbose, console=console)

            status.update("[bold blue]Reading plugin information...")
            plugin_name, version, original_version = get_plugin_info(verbose=verbose, console=console)

            # Version selection
            status.stop()
            major_version = get_major_version(original_version)
            choices = [
                {"name": bump.value, "value": bump.value}
                for bump in VersionBump
            ]
            
            version_choice = inquirer.select(
                message=f"Current Version is {version} - choose the version increment method:",
                choices=choices,
                default=VersionBump.NONE.value,
            ).execute()
            
            status.start()

            # Update version if needed
            bump_type = VersionBump(version_choice)
            if bump_type != VersionBump.NONE:
                new_version = bump_version(original_version, bump_type)
                update_composer_version(new_version, verbose=verbose, console=console)
                version = new_version.lstrip('v')
                if verbose:
                    console.print(f"[dim]→ Version updated to: {new_version}[/]")

            # Build process
            with tempfile.TemporaryDirectory() as temp_dir:
                status.update("[bold blue]Copying plugin files...")
                if verbose:
                    console.print(f"[dim]→ Using temporary directory: {temp_dir}[/]")
                plugin_dir = copy_plugin_files(temp_dir, plugin_name, verbose=verbose, console=console)

                status.update("[bold blue]Creating release info...")
                release_info = create_release_info(plugin_name, branch, commit, version, verbose=verbose, console=console, table_style="panel")
                print(release_info)
                with open(os.path.join(plugin_dir, 'release_info.txt'), 'w') as f:
                    f.write(str(release_info))

                console.print("-------------------------------------------------------")
                status.update("[bold blue]Creating ZIP archive...")
                zip_name = f"{plugin_name}-v{version}.zip"
                zip_path = os.path.join(output_dir, zip_name)
                create_archive(output_dir, plugin_name, version, temp_dir, verbose, console)

                # Copy manuals if MANUALS_DIR is configured
                manuals_dir = get_manuals_dir(verbose=verbose, console=console)
                if manuals_dir:
                    status.update("[bold blue]Copying manuals...")
                    copy_manuals(plugin_name, version, manuals_dir, verbose=verbose, console=console)


                # ---- Get remote config and sync if enabled
                console.print("-------------------------------------------------------")
                sync_status = None
                download_url = None
                remote_config = get_remote_config(plugin_name, verbose=verbose, console=console)
                if remote_config:
                    if no_sync:
                        sync_status = False
                        console.print("[yellow]Remote sync is disabled by --no-sync flag[/]")
                    else:
                        status.update("[bold blue]Syncing to remote server...")
                        zip_file_rsync_path = sync_to_remote(zip_path, remote_config, verbose=verbose, console=console)
                        sync_status = True
                        download_url = _get_download_url(zip_file_rsync_path)

        # Send Slack notification if enabled and sync was successful
        slack_status = None
        if notify_slack and sync_status:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            slack_status = send_release_notification(
                plugin_name=plugin_name,
                version=version,
                branch=branch,
                commit=commit,
                download_url=download_url,  # Using the sync URL as the download link
                webhook_url=webhook_url,
                verbose=verbose,
                console=console
            )

        _show_success_message(plugin_name, version, zip_name, output_dir, zip_file_rsync_path, slack_status)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}", style="red")
        raise click.Abort()

def _show_success_message(plugin_name, version, zip_name, output_dir, zip_file_rsync_path, slack_status=None):
    """Display success message after build completion."""
    sync_message = ""
    if zip_file_rsync_path:
        sync_message = f"\n[green]Successfully synced to remote server[/]"
        sync_message += f"\n[green]DL: {_get_download_url(zip_file_rsync_path)}[/]"
    else:
        sync_message = "\n[yellow]Remote sync was disabled[/]"

    slack_message = ""
    if slack_status is True:
        slack_message = "\n[green]Successfully sent Slack notification[/]"
    elif slack_status is False:
        slack_message = "\n[yellow]Failed to send Slack notification[/]"

    console.print(Panel(f"""
[bold green]Plugin successfully built![/]
Plugin: {plugin_name}
Version: v{version}
Archive: {zip_name}
Location: {output_dir}/{zip_name}{sync_message}{slack_message}

[italic]Note: Built packages are stored in the release directory.[/]
    """, title="Success"))

def main():
    """Entry point for the CLI."""
    build_plugin()

if __name__ == '__main__':
    main()
