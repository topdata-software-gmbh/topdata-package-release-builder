"""Plugin operations module."""
import json
import shutil
import os

def get_plugin_info(verbose=False, console=None):
    """Extract plugin information from composer.json."""
    if verbose and console:
        console.print("[dim]→ Reading composer.json file[/]")
    with open('composer.json', 'r') as f:
        composer_data = json.load(f)

    plugin_class = composer_data['extra']['shopware-plugin-class']
    plugin_name = plugin_class.split('\\')[-1]
    version = composer_data['version'].lstrip('v')

    if verbose and console:
        console.print(f"[dim]→ Found plugin class: {plugin_class}[/]")
        console.print(f"[dim]→ Extracted plugin name: {plugin_name}[/]")
        console.print(f"[dim]→ Found version: {version}[/]")
    return plugin_name, version

def copy_plugin_files(temp_dir, plugin_name, verbose=False, console=None):
    """Copy plugin files to temporary directory."""
    plugin_dir = os.path.join(temp_dir, plugin_name)
    ignored_patterns = [
        '.git*',
        'builds',
        '__pycache__',
        '*.pyc',
        'node_modules',
        'tests',
        '.aider*',
        'php-cs-fixer.*',
        '.php-cs-fixer.*',
        'phpstan.*',
        'rector.*',
        'CONVENTIONS.md',
        'bitbucket-pipelines.yml',
    ]
    if verbose and console:
        console.print(f"[dim]→ Creating plugin directory: {plugin_dir}[/]")
        console.print(f"[dim]→ Ignoring patterns: {', '.join(ignored_patterns)}[/]")
    shutil.copytree('.', plugin_dir, ignore=shutil.ignore_patterns(*ignored_patterns))
    if verbose and console:
        console.print(f"[dim]→ Files copied successfully[/]")
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
