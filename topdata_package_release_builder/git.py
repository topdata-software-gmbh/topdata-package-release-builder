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

def check_git_status():
    """Check if there are any unstaged or uncommitted changes."""
    try:
        status = subprocess.check_output(['git', 'status', '--porcelain']).decode().strip()
        return bool(status)
    except subprocess.CalledProcessError as e:
        print(f"Error checking git status: {e}")
        # Depending on desired behavior, you might want to re-raise or return False
        raise

def stage_changes():
    """Stage all changes in the repository."""
    try:
        subprocess.check_output(['git', 'add', '.'])
        print("Staged all changes.")
    except subprocess.CalledProcessError as e:
        print(f"Error staging changes: {e}")
        raise

def commit_and_tag(file_path: str, version: str, message: str):
    """Commit the specified file and create a tag with the given version."""
    try:
        subprocess.check_output(['git', 'add', file_path])
        print(f"Staged {file_path}.")
        subprocess.check_output(['git', 'commit', '-m', message])
        print(f"Committed with message: '{message}'")
        subprocess.check_output(['git', 'tag', version])
        print(f"Created tag: {version}")
    except subprocess.CalledProcessError as e:
        print(f"Error committing or tagging: {e}")
        raise

def push_changes(branch: str, tag: str):
    """Push the current branch and the specified tag to the origin remote."""
    try:
        subprocess.check_output(['git', 'push', 'origin', branch])
        print(f"Pushed branch: {branch}")
        subprocess.check_output(['git', 'push', 'origin', tag])
        print(f"Pushed tag: {tag}")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing changes: {e}")
        raise
