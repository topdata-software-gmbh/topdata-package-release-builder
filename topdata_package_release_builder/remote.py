"""Remote synchronization functionality."""
import subprocess

def sync_to_remote(zip_path, remote_config):
    """Sync the built plugin to a remote server."""
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
    
    subprocess.run(rsync_cmd, check=True)
