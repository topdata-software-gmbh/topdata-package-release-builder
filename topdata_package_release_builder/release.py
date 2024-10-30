"""Release information handling module."""
from datetime import datetime
import subprocess
import pytz
from tabulate import tabulate

def create_release_info(plugin_name, branch, commit, version):
    """Create a plain-text release_info.txt with formatted content."""
    now = datetime.now(pytz.timezone('Europe/Berlin')).isoformat()

    data = [
        ["Plugin", plugin_name],
        ["Branch", branch],
        ["Commit ID", commit],
        ["Version", f"v{version}"],
        ["Created", now]
    ]

    return tabulate(data, tablefmt="grid")

def sync_to_remote(zip_path, remote_path):
    """Sync the built plugin to a remote server."""
    subprocess.run([
        'rsync',
        '-av',
        '--progress',
        zip_path,
        remote_path
    ], check=True)
