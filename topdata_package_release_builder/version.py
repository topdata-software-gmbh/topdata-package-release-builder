"""Version management module."""
import json
from enum import Enum
from typing import Tuple

class VersionBump(Enum):
    """Version increment types."""
    NONE = "No version update"
    PATCH = "Patch"
    MINOR = "Minor"
    MAJOR = "Major"

def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string into tuple of integers."""
    v = version.lstrip('v')
    major, minor, patch = map(int, v.split('.'))
    return major, minor, patch

def bump_version(current_version: str, bump_type: VersionBump) -> str:
    """Increment version according to bump type."""
    if bump_type == VersionBump.NONE:
        return current_version

    major, minor, patch = parse_version(current_version)
    
    if bump_type == VersionBump.MAJOR:
        return f"{major + 1}.0.0"
    elif bump_type == VersionBump.MINOR:
        return f"{major}.{minor + 1}.0"
    elif bump_type == VersionBump.PATCH:
        return f"{major}.{minor}.{patch + 1}"
    
    return current_version

def update_composer_version(new_version: str, verbose: bool = False, console = None) -> None:
    """Update version in composer.json."""
    if verbose and console:
        console.print(f"[dim]→ Updating composer.json version to: {new_version}[/]")
    
    with open('composer.json', 'r') as f:
        composer_data = json.load(f)
    
    composer_data['version'] = new_version
    
    with open('composer.json', 'w') as f:
        json.dump(composer_data, f, indent=4)

def get_major_version(version: str) -> int:
    """Get major version number from version string."""
    major, _, _ = parse_version(version)
    return major
