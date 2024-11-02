"""Git operations module."""
import subprocess

def get_git_info(verbose=False, console=None):
    """Get current git branch and commit information with a short commit ID."""
    if verbose and console:
        console.print("[dim]→ Getting git branch information[/]")
    branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()

    if verbose and console:
        console.print(f"[dim]→ Current branch: {branch}[/]")
        console.print("[dim]→ Getting short commit hash[/]")
    commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
    
    if verbose and console:
        console.print(f"[dim]→ Current commit: {commit}[/]")
    
    return branch, commit
