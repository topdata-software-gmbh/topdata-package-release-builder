"""Remote synchronization functionality."""
import os
import subprocess


def sync_to_remote(zip_path, remote_config, verbose=False, console=None):
    """
    Sync the built plugin to a remote server.

    Args:
        zip_path (str): Local path to the zip file
        remote_config (dict): Remote server configuration
        verbose (bool): Whether to print verbose output
        console (Console): Rich console object for pretty printing

    Returns:
        str: Full remote path including the zip filename
    """
    if verbose and console:
        console.print("[dim]→ Preparing rsync command[/]")

    rsync_cmd = [
        'rsync',
        '-av',
        '--progress',
        '-e', f'ssh -p {remote_config.get("port", "22")}'
    ]

    # Create remote directory if it doesn't exist
    remote_base = remote_config['path'].split(':')[1]
    rsync_cmd.extend(['--rsync-path', f'mkdir -p {remote_base} && rsync'])

    # Get the zip filename from the local path
    zip_filename = os.path.basename(zip_path)

    # Construct full remote path including filename
    remote_path = remote_config['path']
    if not remote_path.endswith('/'):
        remote_path += '/'
    remote_path += zip_filename

    # Add source and destination
    rsync_cmd.extend([zip_path, remote_path])

    if verbose and console:
        console.print(f"[dim]→ Executing rsync command: {' '.join(rsync_cmd)}[/]")

    try:
        subprocess.run(rsync_cmd, check=True)
        if verbose and console:
            console.print("[dim]→ Rsync completed successfully[/]")
        return remote_path
    except subprocess.CalledProcessError as e:
        if verbose and console:
            console.print(f"[red]→ Rsync failed with error: {str(e)}[/]")
        raise