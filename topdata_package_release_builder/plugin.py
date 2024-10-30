"""Plugin operations module."""
import json
import shutil
import os

def get_plugin_info():
    """Extract plugin information from composer.json."""
    with open('composer.json', 'r') as f:
        composer_data = json.load(f)

    plugin_class = composer_data['extra']['shopware-plugin-class']
    plugin_name = plugin_class.split('\\')[-1]
    version = composer_data['version']

    return plugin_name, version

def copy_plugin_files(temp_dir, plugin_name):
    """Copy plugin files to temporary directory."""
    plugin_dir = os.path.join(temp_dir, plugin_name)
    shutil.copytree('.', plugin_dir, ignore=shutil.ignore_patterns(
        '.git*', 'builds', '__pycache__', '*.pyc', 'node_modules', 'tests'
    ))
    return plugin_dir

def create_archive(output_dir, plugin_name, version, temp_dir):
    """Create a ZIP archive of the plugin."""
    return shutil.make_archive(
        os.path.join(output_dir, f"{plugin_name}-v{version}"),
        'zip',
        temp_dir
    )
