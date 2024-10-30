"""Remote synchronization functionality."""
import subprocess

def sync_to_remote(zip_path, remote_config, verbose=False, console=None):
    """Sync the built plugin to a remote server."""
    if verbose and console:
        console.print("[dim]→ Preparing rsync command[/]")
    
    rsync_cmd = [
        'rsync',
        '-av',
        '--progress',
        '-e', f'ssh -p {remote_config.get("port", "22")}'
    ]
    
    # Create remote directory if it doesn't exist
    remote_dir = remote_config['path'].split(':')[1]
    rsync_cmd.extend(['--rsync-path', f'mkdir -p {remote_dir} && rsync'])
    
    # Add source and destination
    rsync_cmd.extend([zip_path, remote_config['path']])
    
    if verbose and console:
        console.print(f"[dim]→ Executing rsync command: {' '.join(rsync_cmd)}[/]")
    
    try:
        subprocess.run(rsync_cmd, check=True)
        if verbose and console:
            console.print("[dim]→ Rsync completed successfully[/]")
        return remote_config['path']
    except subprocess.CalledProcessError as e:
        if verbose and console:
            console.print(f"[red]→ Rsync failed with error: {str(e)}[/]")
        raise
