#!/usr/bin/env python3
"""Command line interface for the Shopware Plugin Builder."""
import os
from pathlib import Path
import tempfile
from rich.console import Console
from rich.panel import Panel
import click
from InquirerPy import inquirer

from .config import load_env, get_remote_config, get_release_dir, get_manuals_dir, get_docs_generator_project_path
from .git import (
    get_git_info, check_git_status, stage_changes, commit_and_tag, push_changes,
    pull_changes_in_repo, commit_and_push_changes, is_git_repository
)
from .plugin import (
    get_plugin_info,
    copy_plugin_files,
    create_archive,
    verify_compiled_files,
)
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
@click.option('--source-dir', default='.', help='Specify plugin source directory (default: current directory)')
@click.option('--no-sync', is_flag=True, help='Disable syncing to remote server')
@click.option('--notify-slack', '-s', is_flag=True, help='Send notification to Slack after successful upload')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--with-foundation', is_flag=True, help='Inject TopdataFoundationSW6 code into the plugin package.')
@click.option('--debug', is_flag=True, help='Enable debug output for timestamp verification')
@click.option('--version-increment', type=click.Choice(['none', 'patch', 'minor', 'major']), help='Specify the version increment method (none, patch, minor, major). Skips interactive prompt.')
def build_plugin(output_dir, source_dir, no_sync, notify_slack, verbose, debug, with_foundation, version_increment):
    zip_file_rsync_path = None
    """
    Build and package Shopware 6 plugin for release.

    Automatically excludes files matching patterns from:
    - .gitignore files in each directory
    - .sw-zip-blacklist in the plugin root

    Options:
    - --source-dir: Specify plugin source directory (default: current directory)
    - --no-sync: Disable syncing to remote server
    - --notify-slack: Send notification to Slack after successful upload
    - --verbose: Enable verbose output
    """
    # Load environment variables
    load_env(verbose=verbose, console=console)
    get_manuals_dir(verbose=verbose, console=console)

    # Validate foundation plugin path if injection is requested
    foundation_plugin_path = None
    if with_foundation:
        foundation_plugin_path = os.getenv('FOUNDATION_PLUGIN_PATH')
        if not foundation_plugin_path or not os.path.isdir(foundation_plugin_path):
            raise click.UsageError(
                "--with-foundation flag was used, but FOUNDATION_PLUGIN_PATH is not set correctly in .env\n"
                f"Path configured: {foundation_plugin_path}"
            )
        if verbose:
            console.print(f"[dim]→ Foundation plugin path: {foundation_plugin_path}[/dim]")

    # Validate source directory
    if not os.path.isdir(source_dir):
        raise click.UsageError(f"Source directory '{source_dir}' does not exist or is not a directory")

    # Check for unstaged changes early
    if check_git_status(source_dir=source_dir):
        console.print("[yellow]Found unstaged changes![/]")
        stage_confirm = inquirer.confirm(
            message="Would you like to stage these changes?",
            default=True
        ).execute()
        if stage_confirm:
            stage_changes(source_dir=source_dir)
        else:
            console.print("[yellow]Skipping staging unstaged changes.[/]")

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
            branch, commit = get_git_info(source_dir=source_dir, verbose=verbose, console=console)

            # ------------------------------------------------------------------
            # Verify timestamps of compiled assets
            # ------------------------------------------------------------------
            status.update("[bold blue]Verifying compiled files...")
            if not verify_compiled_files(
                    source_dir,
                    verbose=verbose,
                    debug=debug,
                    console=console,
            ):
                console.print("[bold red]Build aborted due to outdated compiled files[/]")
                raise click.Abort()

            status.update("[bold blue]Reading plugin information...")
            plugin_name, version, original_version = get_plugin_info(source_dir=source_dir, verbose=verbose, console=console)

            # Version selection
            status.stop()
            major_version = get_major_version(original_version)
            
            version_choice = None
            if version_increment:
                if version_increment == 'patch':
                    version_choice = VersionBump.PATCH.value
                elif version_increment == 'minor':
                    version_choice = VersionBump.MINOR.value
                elif version_increment == 'major':
                    version_choice = VersionBump.MAJOR.value
                elif version_increment == 'none':
                    version_choice = VersionBump.NONE.value
            else:
                # Calculate next versions for display
                choices = []
                for bump in VersionBump:
                    if bump == VersionBump.NONE:
                        next_version = version
                    else:
                        next_version = bump_version(original_version, bump).lstrip('v')
                    choices.append({
                        "name": f"{bump.value} - {next_version}",
                        "value": bump.value
                    })

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

                # Auto commit, tag, and push
                commit_message = f"bump to version {new_version}"
                commit_and_tag('composer.json', new_version, commit_message, source_dir=source_dir, verbose=verbose, console=console)
                push_changes(branch, new_version, source_dir=source_dir, verbose=verbose, console=console)

            # Build process
            with tempfile.TemporaryDirectory() as temp_dir:
                status.update("[bold blue]Copying plugin files...")
                if verbose:
                    console.print(f"[dim]→ Using temporary directory: {temp_dir}[/]")
                plugin_dir = copy_plugin_files(temp_dir, plugin_name, source_dir=source_dir, verbose=verbose, console=console)

                # --- INJECTION STEP ---
                if with_foundation:
                    status.update("[bold blue]Injecting foundation code...")
                    from .foundation_injector import inject_foundation_code  # local import to avoid costs when not used
                    inject_foundation_code(plugin_dir, foundation_plugin_path, console=console)
                # --- END INJECTION STEP ---

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

                # --- Publish Documentation ---
                manuals_dir = get_manuals_dir(verbose=verbose, console=console)
                if manuals_dir:
                    # 1. Copy the files first
                    status.update("[bold blue]Copying manuals...")
                    copy_manuals(plugin_name, version, manuals_dir, source_dir, verbose=verbose, console=console)
                    
                    # 2. Check if the directory is a git repo and then commit/push
                    if is_git_repository(manuals_dir, verbose=verbose, console=console):
                        try:
                            status.update("[bold blue]Publishing manual to git repository...")
                            commit_message = f"docs({plugin_name}): Add manual for v{version}"
                            
                            pull_changes_in_repo(manuals_dir, verbose=verbose, console=console)
                            
                            commit_and_push_changes(
                                repo_path=manuals_dir,
                                commit_message=commit_message,
                                verbose=verbose,
                                console=console
                            )
                        except Exception as e:
                            # If git operations fail, we print an error but don't stop the build,
                            # as the primary goal (creating the zip) was successful.
                            console.print(f"[bold red]Warning:[/] Failed to publish manual to git repository: {e}")
                    elif verbose:
                        console.print(f"[dim]→ MANUALS_DIR '{manuals_dir}' is not a git repository, skipping auto-commit.[/dim]")


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

        # Send Slack notification if enabled
        slack_status = None
        if notify_slack:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if verbose:
                console.print(f"[dim]→ Slack webhook URL: {'configured' if webhook_url else 'missing'}[/]")
            if not webhook_url:
                console.print("[yellow]Warning:[/] SLACK_WEBHOOK_URL not set in .env")
            elif not sync_status and download_url is None:
                console.print("[yellow]Warning:[/] Skipping Slack notification as sync was not successful")
            else:
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

    # Check for documentation setup
    docs_generator_path = get_docs_generator_project_path()
    manuals_dir = get_manuals_dir()
    
    docs_message = ""
    if docs_generator_path and manuals_dir:
        docs_message = f"\n\n[bold blue]Documentation Setup:[/]"
        docs_message += f"\n[green]✓ Docs generator: {docs_generator_path}[/]"
        docs_message += f"\n[green]✓ Manuals directory: {manuals_dir}[/]"
        docs_message += f"\n[dim]Run: cd {docs_generator_path} && ./deploy/deploy.sh[/]"
    elif manuals_dir:
        docs_message = f"\n\n[bold yellow]Documentation Setup:[/]"
        docs_message += f"\n[green]✓ Manuals directory: {manuals_dir}[/]"
        docs_message += f"\n[yellow]⚠ Docs generator not configured[/]"
    elif docs_generator_path:
        docs_message = f"\n\n[bold yellow]Documentation Setup:[/]"
        docs_message += f"\n[green]✓ Docs generator: {docs_generator_path}[/]"
        docs_message += f"\n[yellow]⚠ Manuals directory not configured[/]"
        docs_message += f"\n[dim]Run: cd {docs_generator_path} && ./deploy/deploy.sh[/]"

    console.print(Panel(f"""
[bold green]Plugin successfully built![/]
Plugin: {plugin_name}
Version: v{version}
Archive: {zip_name}
Location: {output_dir}/{zip_name}{sync_message}{slack_message}{docs_message}

[italic]Note: Built packages are stored in the release directory.[/]
    """, title="Success"))

def main():
    """Entry point for the CLI."""
    build_plugin()

if __name__ == '__main__':
    main()
