"""Plugin operations module."""
import json
import shutil
import os
import zipfile
from typing import List
from .tree import build_ascii_directory_tree


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
