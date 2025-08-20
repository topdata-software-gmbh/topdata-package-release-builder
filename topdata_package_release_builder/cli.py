#!/usr/bin/env python3
"""Command line interface for the Shopware Plugin Builder."""
import os
from pathlib import Path
import tempfile
from rich.console import Console
from rich.panel import Panel
import click
from InquirerPy import inquirer  # Needed for staging confirmation

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
    has_foundation_dependency,
)
from .release import create_release_info
from .remote import sync_to_remote
from .slack import send_release_notification
from .version import VersionBump  # Only needed for type reference
from .manual import copy_manuals
from .workflow import handle_versioning_workflow
from .variant import transform_to_variant

console = Console()


def _get_foundation_path(source_dir: str, verbose: bool, console) -> str | None:
    """
    Determines the path to the foundation plugin, prioritizing environment variables
    over a default relative path.
    """
    # 1. Check for an explicit override from the environment variable.
    foundation_path_env = os.getenv('FOUNDATION_PLUGIN_PATH')
    if foundation_path_env:
        if verbose:
            console.print("[dim]→ Using FOUNDATION_PLUGIN_PATH from environment.[/dim]")
        path_to_check = Path(foundation_path_env)
    else:
        # 2. If no override, construct the default path relative to the target plugin.
        # e.g., if source_dir is '.../my-plugin', this will be '.../topdata-foundation-sw6'
        if verbose:
            console.print("[dim]→ FOUNDATION_PLUGIN_PATH not set, checking default relative path.[/dim]")
        default_path = Path(source_dir).resolve().parent / 'topdata-foundation-sw6'
        path_to_check = default_path

    # 3. Validate the determined path.
    if path_to_check.is_dir():
        if verbose:
            console.print(f"[dim]→ Valid foundation plugin path found: {path_to_check.resolve()}[/dim]")
        return str(path_to_check.resolve())

    if verbose:
        console.print(f"[yellow]→ Foundation plugin not found at checked path: {path_to_check}[/yellow]")
    return None


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
@click.option('--with-foundation', is_flag=True, help='Force injection of TopdataFoundationSW6 code even if plugin does not declare it as dependency.')
@click.option('--debug', is_flag=True, help='Enable debug output for timestamp verification')
@click.option('--version-increment', type=click.Choice(['none', 'patch', 'minor', 'major']), help='Specify the version increment method (none, patch, minor, major). Skips interactive prompt.')
@click.option('--variant-prefix', default=None, help='Add a prefix to create a renamed variant package (e.g., "Free").')
@click.option('--variant-suffix', default=None, help='Add a suffix to create a renamed variant package.')
def build_plugin(output_dir, source_dir, no_sync, notify_slack, verbose, debug, with_foundation, version_increment, variant_prefix, variant_suffix):
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
    should_inject = with_foundation
    
    # Phase 2: Automatic injection based on composer.json
    if not should_inject:
        # Check if foundation is a dependency in composer.json
        if has_foundation_dependency(source_dir, verbose=verbose, console=console):
            should_inject = True
            if verbose:
                console.print("[dim]→ Foundation dependency detected in composer.json, enabling injection[/dim]")
    
    if should_inject:
        foundation_plugin_path = _get_foundation_path(source_dir, verbose, console)
        if not foundation_plugin_path:
            raise click.UsageError(
                "Foundation plugin injection requested but foundation plugin not found.\n"
                "Please ensure the foundation plugin is available at the expected location "
                "or set FOUNDATION_PLUGIN_PATH in your .env file."
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
            version = handle_versioning_workflow(
                original_version=original_version,
                current_version=version,
                branch=branch,
                source_dir=source_dir,
                version_increment_cli=version_increment,
                console=console,
                verbose=verbose
            )
            status.start()

            # Build process
            with tempfile.TemporaryDirectory() as temp_dir:
                status.update("[bold blue]Copying plugin files...")
                if verbose:
                    console.print(f"[dim]→ Using temporary directory: {temp_dir}[/]")
                plugin_dir = copy_plugin_files(temp_dir, plugin_name, source_dir=source_dir, verbose=verbose, console=console)

                # --- INJECTION STEP ---
                if should_inject:
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

                # ---- Handle variant creation if requested
                variant_info = None
                if variant_prefix or variant_suffix:
                    status.update("[bold blue]Creating variant package...")
                    
                    # Create second temporary directory for variant processing
                    with tempfile.TemporaryDirectory() as variant_temp_dir:
                        if verbose:
                            console.print(f"[dim]→ Using variant temporary directory: {variant_temp_dir}[/]")
                        
                        # Copy plugin files to variant directory
                        variant_plugin_dir = copy_plugin_files(
                            variant_temp_dir,
                            plugin_name,
                            source_dir=source_dir,
                            verbose=verbose,
                            console=console
                        )
                        
                        # Apply variant transformation
                        variant_name = transform_to_variant(
                            Path(variant_plugin_dir),
                            plugin_name,
                            prefix=variant_prefix or "",
                            suffix=variant_suffix or "",
                            console=console
                        )
                        
                        # Create release info for variant
                        variant_release_info = create_release_info(
                            variant_name,
                            branch,
                            commit,
                            version,
                            verbose=verbose,
                            console=console,
                            table_style="panel"
                        )
                        print(variant_release_info)
                        with open(os.path.join(variant_temp_dir, variant_name, 'release_info.txt'), 'w') as f:
                            f.write(str(variant_release_info))
                        
                        # Create variant ZIP archive
                        variant_zip_name = f"{variant_name}-v{version}.zip"
                        variant_zip_path = os.path.join(output_dir, variant_zip_name)
                        create_archive(output_dir, variant_name, version, variant_temp_dir, verbose, console)
                        
                        # Sync variant to remote if enabled
                        variant_sync_status = None
                        variant_download_url = None
                        variant_zip_file_rsync_path = None
                        if remote_config and not no_sync:
                            status.update("[bold blue]Syncing variant to remote server...")
                            variant_zip_file_rsync_path = sync_to_remote(
                                variant_zip_path,
                                remote_config,
                                verbose=verbose,
                                console=console
                            )
                            variant_sync_status = True
                            variant_download_url = _get_download_url(variant_zip_file_rsync_path)
                        
                        variant_info = {
                            'name': variant_name,
                            'zip_name': variant_zip_name,
                            'zip_path': variant_zip_path,
                            'sync_status': variant_sync_status,
                            'download_url': variant_download_url,
                            'zip_file_rsync_path': variant_zip_file_rsync_path
                        }

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
                variant_info=variant_info,  # Add this line
                verbose=verbose,
                console=console
            )

        _show_success_message(plugin_name, version, zip_name, output_dir, zip_file_rsync_path, slack_status, variant_info)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}", style="red")
        raise click.Abort()

def _show_success_message(plugin_name, version, zip_name, output_dir, zip_file_rsync_path, slack_status=None, variant_info=None):
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

    # Build main package info
    main_package_info = f"""
[bold green]Main Package:[/]
Plugin: {plugin_name}
Version: v{version}
Archive: {zip_name}
Location: {output_dir}/{zip_name}{sync_message}"""

    # Build variant package info if available
    variant_package_info = ""
    if variant_info:
        variant_sync_message = ""
        if variant_info['zip_file_rsync_path']:
            variant_sync_message = f"\n[green]Successfully synced to remote server[/]"
            variant_sync_message += f"\n[green]DL: {_get_download_url(variant_info['zip_file_rsync_path'])}[/]"
        
        variant_package_info = f"""
[bold blue]Variant Package:[/]
Plugin: {variant_info['name']}
Version: v{version}
Archive: {variant_info['zip_name']}
Location: {output_dir}/{variant_info['zip_name']}{variant_sync_message}"""

    console.print(Panel(f"""
[bold green]Plugin successfully built![/]
{main_package_info}{variant_package_info}{slack_message}{docs_message}

[italic]Note: Built packages are stored in the release directory.[/]
    """, title="Success"))

def main():
    """Entry point for the CLI."""
    build_plugin()

if __name__ == '__main__':
    main()
