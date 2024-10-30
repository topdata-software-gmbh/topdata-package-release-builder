"""Configuration module for environment variables."""
from pathlib import Path
from dotenv import load_dotenv
import os

def load_env(verbose=False, console=None):
    """Load environment variables from .env file."""
    env_path = Path('.env')
    if verbose and console:
        console.print(f"[dim]→ Loading environment from: {env_path}[/]")
    load_dotenv(env_path)

def get_remote_config(plugin_name, verbose=False, console=None):
    """Get remote configuration from environment variables."""
    if verbose and console:
        console.print("[dim]→ Reading remote configuration[/]")
    
    host = os.getenv('RSYNC_SSH_HOST')
    port = os.getenv('RSYNC_SSH_PORT', '22')
    base_path = os.getenv('RSYNC_REMOTE_PATH_RELEASES_FOLDER', '')
    
    if verbose and console:
        console.print(f"[dim]→ Found host: {host or 'Not set'}[/]")
        console.print(f"[dim]→ Found port: {port}[/]")
        console.print(f"[dim]→ Found base path: {base_path or 'Not set'}[/]")
    
    if not all([host, base_path]):
        if verbose and console:
            console.print("[yellow]→ Missing required remote configuration (host or base path)[/]")
        return None
        
    # Ensure the base path ends with a trailing slash
    base_path = base_path.rstrip('/') + '/'
    # Construct the full remote path including plugin directory
    remote_path = f"{host}:{base_path}{plugin_name}/"
    
    return {
        'host': host,
        'port': port,
        'path': remote_path
    }
