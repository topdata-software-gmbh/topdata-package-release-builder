"""Release information handling module."""
from datetime import datetime
import subprocess
import pytz

def _create_table(data):
    """Create a minimal ASCII table with box-drawing characters."""
    # Find the maximum width for each column
    col_widths = [max(len(str(row[i])) for row in data) for i in range(2)]
    
    # Create the table string
    lines = []
    
    # Top border
    lines.append(f"┌{'─' * (col_widths[0] + 2)}┬{'─' * (col_widths[1] + 2)}┐")
    
    # Data rows
    for key, value in data:
        lines.append(f"│ {key:<{col_widths[0]}} │ {value:<{col_widths[1]}} │")
    
    # Bottom border
    lines.append(f"└{'─' * (col_widths[0] + 2)}┴{'─' * (col_widths[1] + 2)}┘")
    
    return '\n'.join(lines)

def create_release_info(plugin_name, branch, commit, version):
    """Create a plain-text release_info.txt with formatted content."""
    now = datetime.now(pytz.timezone('Europe/Berlin')).isoformat()

    data = [
        ["Plugin", plugin_name],
        ["Version", f"v{version}"],
        ["Created", now],
        ["Branch", branch],
        ["Commit ID", commit]
    ]

    return _create_table(data)

def sync_to_remote(zip_path, remote_path):
    """Sync the built plugin to a remote server."""
    subprocess.run([
        'rsync',
        '-av',
        '--progress',
        zip_path,
        remote_path
    ], check=True)