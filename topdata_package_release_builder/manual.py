"""Module for handling manual/documentation copying."""
from pathlib import Path
import shutil

def copy_manuals(plugin_name: str, version: str, manuals_dir: str, verbose: bool = False, console = None):
    """
    Copy manuals folder to the specified manual directory.
    
    Args:
        plugin_name (str): Name of the plugin
        version (str): Version of the plugin
        manuals_dir (str): Base directory for manuals
        verbose (bool): Enable verbose output
        console: Rich console instance for output
    """
    if verbose and console:
        console.print("[dim]→ Copying manuals...[/]")
    
    source_dir = Path('manual')
    if not source_dir.exists():
        if verbose and console:
            console.print(f"[yellow]→ No manual dir {source_dir} found, skipping[/]")
        return
    
    # Copy each language directory
    try:
        for lang_dir in source_dir.iterdir():
            if lang_dir.is_dir():
                # Create target directory structure for each language
                target_dir = Path(manuals_dir) / lang_dir.name / plugin_name / version
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy the contents
                shutil.copytree(lang_dir, target_dir, dirs_exist_ok=True)
                if verbose and console:
                    console.print(f"[blue]→ Copied {lang_dir.name} manual to: {target_dir}[/]")
    except Exception as e:
        if verbose and console:
            console.print(f"[red]→ Error copying manual: {str(e)}[/]")
        raise
