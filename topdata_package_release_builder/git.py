"""Git operations module."""
import subprocess
import os

def get_git_info(source_dir='.', verbose=False, console=None):
    """Get current git branch and commit information with a short commit ID."""
    original_dir = os.getcwd()
    try:
        os.chdir(source_dir)
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
    finally:
        os.chdir(original_dir)

def check_git_status(source_dir='.', verbose=False, console=None):
    """Check if there are any unstaged or uncommitted changes."""
    original_dir = os.getcwd()
    try:
        os.chdir(source_dir)
        try:
            status = subprocess.check_output(['git', 'status', '--porcelain']).decode().strip()
            return bool(status)
        except subprocess.CalledProcessError as e:
            if verbose and console:
                console.print(f"[dim]→ Error checking git status: {e}[/]")
            # Depending on desired behavior, you might want to re-raise or return False
            return False
    finally:
        os.chdir(original_dir)

def stage_changes(source_dir='.', verbose=False, console=None):
    """Stage all changes in the repository."""
    original_dir = os.getcwd()
    try:
        os.chdir(source_dir)
        try:
            subprocess.check_output(['git', 'add', '.'])
            if verbose and console:
                console.print("[dim]→ Staged all changes[/]")
        except subprocess.CalledProcessError as e:
            if verbose and console:
                console.print(f"[dim]→ Error staging changes: {e}[/]")
            raise
    finally:
        os.chdir(original_dir)

def commit_and_tag(file_path: str, version: str, message: str, source_dir='.', verbose=False, console=None):
    """Commit the specified file and create a tag with the given version."""
    original_dir = os.getcwd()
    try:
        os.chdir(source_dir)
        try:
            subprocess.check_output(['git', 'add', file_path])
            if verbose and console:
                console.print(f"[dim]→ Staged {file_path}[/]")
            subprocess.check_output(['git', 'commit', '-m', message])
            if verbose and console:
                console.print(f"[dim]→ Committed with message: '{message}'[/]")
            subprocess.check_output(['git', 'tag', version])
            if verbose and console:
                console.print(f"[dim]→ Created tag: {version}[/]")
        except subprocess.CalledProcessError as e:
            if verbose and console:
                console.print(f"[dim]→ Error committing or tagging: {e}[/]")
            raise
    finally:
        os.chdir(original_dir)

def push_changes(branch: str, tag: str, source_dir='.', verbose=False, console=None):
    """Push the current branch and the specified tag to the origin remote."""
    original_dir = os.getcwd()
    try:
        os.chdir(source_dir)
        try:
            subprocess.check_output(['git', 'push', 'origin', branch])
            if verbose and console:
                console.print(f"[dim]→ Pushed branch: {branch}[/]")
            subprocess.check_output(['git', 'push', 'origin', tag])
            if verbose and console:
                console.print(f"[dim]→ Pushed tag: {tag}[/]")
        except subprocess.CalledProcessError as e:
            if verbose and console:
                console.print(f"[dim]→ Error pushing changes: {e}[/]")
            raise
    finally:
        os.chdir(original_dir)
