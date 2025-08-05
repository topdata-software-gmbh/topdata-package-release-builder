"""Plugin operations module.

Utility helpers for working with plugin source files live here. This now
includes timestamp verification helpers that ensure compiled assets are up to
date before we proceed with building a release package.  These helpers are
kept inside the ``plugin`` module so that other modules (e.g. ``cli``) can
import them without introducing an additional dependency or circular import.
"""
import json
import shutil
import os
import zipfile
from pathlib import Path
from typing import List, Iterable
from .tree import build_ascii_directory_tree
import time


def get_plugin_info(source_dir='.', verbose=False, console=None):
    """
    Extract plugin information from composer.json.

    Args:
        source_dir (str): The directory containing the plugin source code.
        verbose (bool): Enable verbose output.
        console (Console): Rich console instance for output.

    Returns:
        tuple: (plugin_name, version, original_version)
    """
    if verbose and console:
        console.print("[dim]→ Reading composer.json file[/]")
    with open(os.path.join(source_dir, 'composer.json'), 'r') as f:
        composer_data = json.load(f)

    plugin_class = composer_data['extra']['shopware-plugin-class']
    plugin_name = plugin_class.split('\\')[-1]
    version = composer_data['version'].lstrip('v')

    if verbose and console:
        console.print(f"[dim]→ Found plugin class: {plugin_class}[/]")
        console.print(f"[dim]→ Extracted plugin name: {plugin_name}[/]")
        console.print(f"[dim]→ Found version: {version}[/]")
    return plugin_name, version, composer_data['version']  # Return original version string too

def copy_plugin_files(temp_dir, plugin_name, source_dir='.', verbose=False, console=None):
    """
    Copy plugin files to temporary directory.

    Args:
        temp_dir (str): The temporary directory to copy files to.
        plugin_name (str): The name of the plugin.
        source_dir (str): The directory containing the plugin source code.
        verbose (bool): Enable verbose output.
        console (Console): Rich console instance for output.

    Returns:
        str: Path to the copied plugin directory.
    """
    plugin_dir = os.path.join(temp_dir, plugin_name)
    ignored_patterns = [
        '.git*',
        'builds',
        '__pycache__',
        '*.pyc',
        'node_modules',
        'tests',
        '.idea',
        'php-cs-fixer.*',
        '.php-cs-fixer.*',
        'phpstan.*',
        'rector.*',
        'bitbucket-pipelines.yml',
        '.sw-zip-blacklist',
        # ---- AI stuff ----
        '.aider*',
        'ai_docs',
        '.roo*',
        '.cursor*',
        '.windsurf*',
        'CONVENTIONS.md',
        'CONVENTIONS-*.md',
        'CLAUDE.md',
        'repomix-output.txt',
    ]

    # Read .sw-zip-blacklist if it exists
    blacklist_file = os.path.join(source_dir, '.sw-zip-blacklist')
    if os.path.exists(blacklist_file):
        if verbose and console:
            console.print(f"[dim]→ Reading {blacklist_file}[/]")
        with open(blacklist_file, 'r') as f:
            # Add each non-empty line from the blacklist file
            numAdded = 0
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignored_patterns.append(line)
                    numAdded += 1
            if verbose and console:
                console.print(f"[dim]→ Added {numAdded} patterns from {blacklist_file}[/]")
    if verbose and console:
        console.print(f"[dim]→ Creating plugin directory: {plugin_dir}[/]")
        console.print(f"[dim]→ Ignoring patterns: {', '.join(ignored_patterns)}[/]")
    shutil.copytree(source_dir, plugin_dir, ignore=shutil.ignore_patterns(*ignored_patterns))
    if verbose and console:
        console.print(f"[dim]→ Files copied successfully[/]")
        # show tree structure
        console.print(build_ascii_directory_tree(plugin_dir, exclude_patterns=['.git', '__pycache__'], max_depth=2))

    return plugin_dir

# ---------------------------------------------------------------------------
# Timestamp verification helpers
# ---------------------------------------------------------------------------

def get_newest_mtime(directory: str, extensions: Iterable[str]) -> tuple[float, str, int]:
    """Return the newest *modification* timestamp found in *directory*.

    Args:
        directory: The directory to walk recursively.
        extensions: A collection of file-extensions that *must* start with a
            dot (``.``).

    Returns
    -------
    float
        A POSIX timestamp representing the newest ``mtime`` found amongst all
        matching files.  If *directory* (or any matching file) does not exist
        the function returns ``0`` so that comparison logic can still work
        without special-casing *None*.
    """
    if not os.path.exists(directory):
        # Directory does not exist – return neutral tuple so that callers can still compare timestamps
        return 0, "", 0

    newest: float = 0
    newest_file: str = ""
    file_count: int = 0
    for root, _dirs, files in os.walk(directory):
        for file_name in files:
            if any(file_name.endswith(ext) for ext in extensions):
                file_count += 1
                path = os.path.join(root, file_name)
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    # If the file disappears mid-walk just ignore it – it is
                    # not relevant for deciding whether to abort a build.
                    continue
                if mtime > newest:
                    newest = mtime
                    newest_file = path
    return newest, newest_file, file_count


# In file: topdata_package_release_builder/plugin.py

def verify_compiled_files(
        source_dir: str = '.',
        *,
        verbose: bool = False,
        debug: bool = False,
        console=None,
) -> bool:
    """
    Verify that compiled assets in `public/` are newer than sources in `app/`.
    This check is type-based and handles both administration and storefront assets.
    """

    checks = [
        {
            "type": "Administration JS",
            "src_path": os.path.join(source_dir, "src/Resources/app/administration/src"),
            "dist_path": os.path.join(source_dir, "src/Resources/public/administration/js"),
            "src_ext": ('.ts', '.js'),
            "dist_ext": ('.js',),
        },
        {
            "type": "Storefront JS",
            "src_path": os.path.join(source_dir, "src/Resources/app/storefront/src"),
            "dist_path": os.path.join(source_dir, "src/Resources/public/storefront/js"),
            "src_ext": ('.ts', '.js'),
            "dist_ext": ('.js',),
        },
        {
            "type": "Storefront CSS",
            "src_path": os.path.join(source_dir, "src/Resources/app/storefront/src"),
            "dist_path": os.path.join(source_dir, "src/Resources/public/storefront/css"),
            "src_ext": ('.scss', '.css'),
            "dist_ext": ('.css',),
        },
    ]

    all_errors: list[str] = []

    for check in checks:
        if not os.path.exists(check["src_path"]):
            if verbose and console:
                console.print(f'[dim]→ Skipping check for {check["type"]}: source directory not found.[/dim]')
            continue

        src_time, src_file, src_count = get_newest_mtime(check["src_path"], check["src_ext"])
        dist_time, dist_file, dist_count = get_newest_mtime(check["dist_path"], check["dist_ext"])

        # Only check if source files exist.
        if src_count > 0 and dist_count > 0 and src_time > dist_time:
            error_msg = (
                f'{check["type"]}: Source ({time.ctime(src_time) if src_time else "N/A"}) > '
                f'Compiled ({time.ctime(dist_time) if dist_time else "N/A"})'
            )
            all_errors.append(error_msg)
            if debug and console:
                console.print(
                    f'- Outdated {check["type"]} found:\n'
                    f"       Source File: {src_file or 'unknown'}\n"
                    f"  vs. Compiled File: {dist_file or 'unknown'}"
                )

    if all_errors:
        if console:
            console.print("[bold red]Error: Compiled files are outdated[/]")
            for err in all_errors:
                console.print(f"- {err}")
        return False

    if verbose and console:
        console.print("[green]✓ Compiled assets are up-to-date[/]")
    return True


# ---------------------------------------------------------------------------
# Existing helpers
# ---------------------------------------------------------------------------

def create_archive(output_dir, plugin_name, version, temp_dir, verbose=False, console=None):
    """Create a ZIP archive of the plugin."""
    archive_path = os.path.join(output_dir, f"{plugin_name}-v{version}")
    if verbose and console:
        console.print(f"[dim]→ Creating ZIP archive: {archive_path}.zip[/]")
        console.print(f"[dim]→ Source directory: {temp_dir}[/]")
    result = shutil.make_archive(archive_path, 'zip', temp_dir)
    if verbose and console:
        console.print(f"[dim]→ Archive created successfully[/]")
    return result

def has_foundation_dependency(source_dir='.', verbose=False, console=None) -> bool:
    """Checks if the plugin's composer.json requires the foundation plugin."""
    composer_path = Path(source_dir) / 'composer.json'
    if not composer_path.is_file():
        return False

    try:
        with open(composer_path, 'r', encoding='utf-8') as f:
            composer_data = json.load(f)

        has_dep = 'topdata/topdata-foundation-sw6' in composer_data.get('require', {})
        if verbose and console:
            console.print(f"[dim]→ Checking for foundation dependency in composer.json: {'[green]Yes[/green]' if has_dep else 'No'}[/dim]")
        return has_dep
    except (json.JSONDecodeError, IOError):
        if verbose and console:
            console.print(f"[yellow]Warning: Could not parse {composer_path}[/yellow]")
        return False