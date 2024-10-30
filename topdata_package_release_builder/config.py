"""Configuration module for environment variables."""
from pathlib import Path
from dotenv import load_dotenv
import os

def load_env():
    """Load environment variables from .env file."""
    env_path = Path('.env')
    load_dotenv(env_path)

def get_remote_config(plugin_name):
    """Get remote configuration from environment variables."""
    host = os.getenv('RSYNC_SSH_HOST')
    port = os.getenv('RSYNC_SSH_PORT', '22')
    base_path = os.getenv('RSYNC_REMOTE_PATH_RELEASES_FOLDER', '')
    
    if not all([host, base_path]):
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
