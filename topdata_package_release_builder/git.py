"""Git operations module."""
import subprocess

def get_git_info():
    """Get current git branch and commit information."""
    branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    return branch, commit
