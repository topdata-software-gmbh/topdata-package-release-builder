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


def verify_compiled_files(
    source_dir: str = '.',
    *,
    src_path: str = 'src/Resources/app/storefront/src',
    dist_path: str = 'src/Resources/app/storefront/dist',
    verbose: bool = False,
    debug: bool = False,
    console=None,
) -> bool:
    """Verify that the compiled assets in *dist/* are newer than sources in *src/*.

    The check is *type-based* – we do **not** attempt to map individual source
    files to their compiled output.  Instead we take the **newest** timestamp
    of relevant source file-types (TS/JS and SCSS/CSS) inside ``src/`` and
    compare them with the newest timestamps of their compiled counterparts in
    ``dist/``.  If any source timestamp is newer, the function returns
    ``False`` and can be used by the caller to abort the build.

    Parameters
    ----------
    source_dir:
        Absolute or relative path of the plugin root directory.  The function
        derives ``src/`` and ``dist/`` paths from it.
    verbose:
        If *True* we print diagnostic information to *console* (when given).
    console:
        An optional *rich.console.Console* instance used for coloured output.

    Returns
    -------
    bool
        ``True`` if **all** compiled timestamps are newer or equal to the
        newest source timestamps; ``False`` otherwise.
    """
    src_dir = os.path.join(source_dir, src_path)
    dist_dir = os.path.join(source_dir, dist_path)

    # Collect newest timestamps (plus example files and counts).
    js_sources, js_source_file, js_source_count = get_newest_mtime(src_dir, ('.ts', '.js'))
    css_sources, css_source_file, css_source_count = get_newest_mtime(src_dir, ('.scss', '.css'))
    js_compiled, js_compiled_file, js_compiled_count = get_newest_mtime(dist_dir, ('.js',))
    css_compiled, css_compiled_file, css_compiled_count = get_newest_mtime(dist_dir, ('.css',))

    # ------------------------------------------------------------------
    # Compare timestamps
    # ------------------------------------------------------------------
    errors: list[str] = []
    # Only perform timestamp comparison if both source and compiled files of a given type exist.
    # This handles the valid case where a plugin provides source files (e.g., SCSS for variables)
    # but does not compile them into its own dist/ folder.
    if js_source_count > 0 and js_compiled_count > 0 and js_sources > js_compiled:
        errors.append(
            f"JavaScript: Source ({time.ctime(js_sources) if js_sources else 'N/A'}) > "
            f"Compiled ({time.ctime(js_compiled) if js_compiled else 'N/A'})"
        )

    if css_source_count > 0 and css_compiled_count > 0 and css_sources > css_compiled:
        errors.append(
            f"CSS: Source ({time.ctime(css_sources) if css_sources else 'N/A'}) > "
            f"Compiled ({time.ctime(css_compiled) if css_compiled else 'N/A'})"
        )

    if errors:
        if console:
            console.print("[bold red]Error: Compiled files are outdated[/]")
            for err in errors:
                console.print(f"- {err}")

            # Overview statistics
            console.print(f"\n[bold]Source directory:[/] {src_dir} "
                          f"({js_source_count} JS/TS, {css_source_count} CSS/SCSS files)")
            console.print(f"[bold]Compiled directory:[/] {dist_dir} "
                          f"({js_compiled_count} JS, {css_compiled_count} CSS files)")

            if debug:
                console.print("\n[bold]Specific files causing issues:[/]")
                if js_source_count > 0 and js_compiled_count > 0 and js_sources > js_compiled:
                    console.print(
                        f"- JS: {js_source_file or 'unknown'} ({time.ctime(js_sources)})\n"
                        f"       vs {js_compiled_file or 'unknown'} ({time.ctime(js_compiled) if js_compiled else 'N/A'})"
                    )
                if css_source_count > 0 and css_compiled_count > 0 and css_sources > css_compiled:
                    console.print(
                        f"- CSS: {css_source_file or 'unknown'} ({time.ctime(css_sources)})\n"
                        f"        vs {css_compiled_file or 'unknown'} ({time.ctime(css_compiled) if css_compiled else 'N/A'})"
                    )
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