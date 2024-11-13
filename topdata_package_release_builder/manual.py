"""Module for handling manual/documentation copying."""
from pathlib import Path
import shutil
import subprocess

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
    
    # Create target directory structure
    try:
        target_dir = Path(manuals_dir) / plugin_name / f"v{version}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean target directory if it exists
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        # Copy the contents using rsync to ensure clean copy
        try:
            subprocess.run(
                ['rsync', '-a', '--delete', f"{source_dir}/", f"{target_dir}/"],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            # Fallback to shutil if rsync fails
            shutil.copytree(source_dir, target_dir)
        if verbose and console:
            console.print(f"[blue]→ Copied manual to: {target_dir}[/]")
    except Exception as e:
        if verbose and console:
            console.print(f"[red]→ Error copying manual: {str(e)}[/]")
        raise
