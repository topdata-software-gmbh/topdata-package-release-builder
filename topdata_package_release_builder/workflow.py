# topdata_package_release_builder/workflow.py
"""
Houses self-contained business logic workflows extracted from the main CLI.

This module helps to keep the cli.py file clean and focused on command-line
argument parsing and high-level orchestration.
"""
from InquirerPy import inquirer

from .config import get_manuals_dir
from .git import (commit_and_tag, push_changes, is_git_repository,
                  pull_changes_in_repo, commit_and_push_changes)
from .manual import copy_manuals
from .version import VersionBump, bump_version, update_composer_version


def handle_versioning_workflow(
    original_version: str,
    current_version: str,
    branch: str,
    source_dir: str,
    version_increment_cli: str | None,
    console,
    verbose: bool
) -> str:
    """
    Handles the user interaction for version bumping, updates files, and commits to git.
    Returns the selected version string (without 'v' prefix).
    """
    from .version import get_major_version
    
    major_version = get_major_version(original_version)
    
    version_choice = None
    if version_increment_cli:
        if version_increment_cli == 'patch':
            version_choice = VersionBump.PATCH.value
        elif version_increment_cli == 'minor':
            version_choice = VersionBump.MINOR.value
        elif version_increment_cli == 'major':
            version_choice = VersionBump.MAJOR.value
        elif version_increment_cli == 'none':
            version_choice = VersionBump.NONE.value
    else:
        # Calculate next versions for display
        choices = []
        for bump in VersionBump:
            if bump == VersionBump.NONE:
                next_version = current_version
            else:
                next_version = bump_version(original_version, bump).lstrip('v')
            choices.append({
                "name": f"{bump.value} - {next_version}",
                "value": bump.value
            })

        version_choice = inquirer.select(
            message=f"Current Version is {current_version} - choose the version increment method:",
            choices=choices,
            default=VersionBump.NONE.value,
        ).execute()

    # Update version if needed
    bump_type = VersionBump(version_choice)
    if bump_type != VersionBump.NONE:
        new_version = bump_version(original_version, bump_type)
        update_composer_version(new_version, verbose=verbose, console=console)
        new_version_str = new_version.lstrip('v')
        if verbose:
            console.print(f"[dim]→ Version updated to: {new_version}[/]")

        # Auto commit, tag, and push
        commit_message = f"bump to version {new_version}"
        commit_and_tag('composer.json', new_version, commit_message, source_dir=source_dir, verbose=verbose, console=console)
        push_changes(branch, new_version, source_dir=source_dir, verbose=verbose, console=console)
        
        return new_version_str
    
    return current_version