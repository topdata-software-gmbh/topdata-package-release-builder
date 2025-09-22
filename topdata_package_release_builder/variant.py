"""
Plugin Variant Creation Module

This module provides functionality to transform a plugin into a variant with
modified identity (name, namespace, FQCN) based on provided prefix/suffix.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
import shutil

from rich.console import Console
from . import string_utils


def transform_to_variant(
    plugin_dir: Path,
    original_name: str,
    prefix: str,
    suffix: str,
    console: Console
) -> str:
    """
    Transform a plugin into a variant with modified identity.
    
    Args:
        plugin_dir: Path to the plugin directory
        original_name: Original plugin name (e.g., "TopdataMachineTranslationsSW6")
        prefix: Prefix to add (e.g., "Free")
        suffix: Suffix to add
        console: Rich console for logging
        
    Returns:
        The new transformed plugin name
    """
    console.print(f"[bold blue]Transforming plugin to variant...[/]")
    
    # Calculate new identity
    new_name = _calculate_new_name(original_name, prefix, suffix)
    original_namespace = f"Topdata\\{original_name}"
    new_namespace = f"Topdata\\{new_name}"
    original_fqcn = f"Topdata\\{original_name}\\{original_name}"
    new_fqcn = f"Topdata\\{new_name}\\{new_name}"
    
    console.print(f"  Original name: {original_name}")
    console.print(f"  New name: {new_name}")
    console.print(f"  Original namespace: {original_namespace}")
    console.print(f"  New namespace: {new_namespace}")
    
    # Load and modify composer.json
    composer_path = plugin_dir / "composer.json"
    if composer_path.exists():
        _modify_composer_json(
            composer_path, 
            new_name, 
            new_namespace, 
            new_fqcn, 
            prefix, 
            suffix
        )
    
    # Rename main PHP file
    _rename_main_php_file(plugin_dir, original_name, new_name, console)
    
    # Perform global find-replace
    _perform_global_replacement(
        plugin_dir,
        original_name,
        new_name,
        original_namespace,
        new_namespace,
        console
    )
    
    # Rename storefront JS assets
    _rename_storefront_js_assets(plugin_dir, original_name, new_name, console)
    
    # Rename root directory
    _rename_root_directory(plugin_dir, original_name, new_name, console)
    
    console.print(f"[green]✓ Plugin transformed to variant: {new_name}[/]")
    return new_name


def _calculate_new_name(original_name: str, prefix: str, suffix: str) -> str:
    """Calculate the new plugin name based on prefix and suffix."""
    new_name = original_name
    
    if prefix:
        new_name = f"{prefix}{original_name}"
    
    if suffix:
        new_name = f"{new_name}{suffix}"
    
    return new_name


def _modify_composer_json(
    composer_path: Path,
    new_name: str,
    new_namespace: str,
    new_fqcn: str,
    prefix: str,
    suffix: str
) -> None:
    """Modify composer.json with new plugin identity."""
    with open(composer_path, 'r', encoding='utf-8') as f:
        composer_data = json.load(f)
    
    # Modify name field
    if 'name' in composer_data:
        original_name = composer_data['name']
        if prefix:
            # Replace the last part after slash with prefixed version
            parts = original_name.split('/')
            if len(parts) == 2:
                package_name = parts[1]
                # Convert camelCase to kebab-case for package name
                kebab_name = string_utils.camel_to_kebab_for_composer(new_name)
                composer_data['name'] = f"{parts[0]}/{kebab_name}"
    
    # Modify extra fields
    if 'extra' in composer_data:
        extra = composer_data['extra']
        
        # Modify label
        if 'label' in extra:
            if isinstance(extra['label'], dict):
                # Handle multilingual labels
                for lang, label in extra['label'].items():
                    extra['label'][lang] = string_utils.prepend_variant_text(label, prefix, suffix)
            else:
                # Handle single string label
                extra['label'] = string_utils.prepend_variant_text(str(extra['label']), prefix, suffix)
        
        # Modify description
        if 'description' in extra:
            if isinstance(extra['description'], dict):
                # Handle multilingual descriptions
                for lang, desc in extra['description'].items():
                    extra['description'][lang] = string_utils.prepend_variant_text(desc, prefix, suffix)
            else:
                # Handle single string description
                extra['description'] = string_utils.prepend_variant_text(str(extra['description']), prefix, suffix)
        
        # Modify shopware-plugin-class
        if 'shopware-plugin-class' in extra:
            extra['shopware-plugin-class'] = new_fqcn
    
    # Modify root description field
    if 'description' in composer_data:
        if isinstance(composer_data['description'], dict):
            # Handle multilingual root descriptions
            for lang, desc in composer_data['description'].items():
                composer_data['description'][lang] = string_utils.prepend_variant_text(desc, prefix, suffix)
        else:
            # Handle single string root description
            composer_data['description'] = string_utils.prepend_variant_text(
                str(composer_data['description']), prefix, suffix
            )
    
    # Modify autoload.psr-4
    if 'autoload' in composer_data and 'psr-4' in composer_data['autoload']:
        autoload = composer_data['autoload']['psr-4']
        
        # Find and replace the old namespace key
        old_namespace_key = None
        for key in list(autoload.keys()):
            if key.startswith('Topdata\\'):
                old_namespace_key = key
                break
        
        if old_namespace_key:
            autoload[new_namespace + '\\'] = autoload[old_namespace_key]
            del autoload[old_namespace_key]
    
    # Save the modified composer.json
    with open(composer_path, 'w', encoding='utf-8') as f:
        json.dump(composer_data, f, indent=4, ensure_ascii=False)


def _rename_main_php_file(
    plugin_dir: Path,
    original_name: str,
    new_name: str,
    console: Console
) -> None:
    """Rename the main plugin PHP file in src/ directory."""
    src_dir = plugin_dir / "src"
    if not src_dir.exists():
        return
    
    original_file = src_dir / f"{original_name}.php"
    new_file = src_dir / f"{new_name}.php"
    
    if original_file.exists():
        original_file.rename(new_file)
        console.print(f"  Renamed: {original_file.name} -> {new_file.name}")


def _perform_global_replacement(
    plugin_dir: Path,
    original_name: str,
    new_name: str,
    original_namespace: str,
    new_namespace: str,
    console: Console
) -> None:
    """Perform global find-replace across all relevant files."""
    # File extensions to process
    extensions = {'.php', '.xml', '.js', '.twig', '.json', '.yml', '.yaml', '.md'}
    
    files_processed = 0
    replacements_made = 0
    
    for file_path in plugin_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Replace namespace
                content = content.replace(original_namespace, new_namespace)
                
                # Replace class name (exact matches)
                content = re.sub(
                    r'\b' + re.escape(original_name) + r'\b',
                    new_name,
                    content
                )
                
                # Replace in file paths/comments (case sensitive)
                content = content.replace(
                    f"Topdata/{original_name}",
                    f"Topdata/{new_name}"
                )
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_processed += 1
                    replacements_made += 1
            except (UnicodeDecodeError, IOError):
                # Skip binary files or files that can't be read
                continue
    
    console.print(f"  Processed {files_processed} files with replacements")


def _rename_storefront_js_assets(
    plugin_dir: Path,
    original_name: str,
    new_name: str,
    console: Console
) -> None:
    """Rename storefront JS assets directory and files."""
    js_dist_dir = plugin_dir / "src" / "Resources" / "app" / "storefront" / "dist" / "storefront" / "js"
    
    if not js_dist_dir.exists():
        console.print(f"[yellow]  Warning: JS dist directory not found: {js_dist_dir}[/]")
        return
    
    # Convert names to kebab-case for directory naming
    original_kebab = string_utils.camel_to_kebab_for_js_asset(original_name)
    new_kebab = string_utils.camel_to_kebab_for_js_asset(new_name)
    
    # Rename directory
    original_dir = js_dist_dir / original_kebab
    new_dir = js_dist_dir / new_kebab
    
    if original_dir.exists():
        original_dir.rename(new_dir)
        console.print(f"  Renamed JS directory: {original_dir.name} -> {new_dir.name}")
    else:
        console.print(f"[bold yellow]  Warning: Original JS directory not found. Looked for: {original_dir}[/bold yellow]")
        return  # Exit if directory was not found
    
    # Rename JS file
    original_js_in_new_dir = new_dir / f"{original_kebab}.js"
    new_js = new_dir / f"{new_kebab}.js"
    
    if original_js_in_new_dir.exists():
        original_js_in_new_dir.rename(new_js)
        console.print(f"  Renamed JS file: {original_js_in_new_dir.name} -> {new_js.name}")
    else:
        console.print(f"[yellow]  Warning: JS file not found in new directory: {original_js_in_new_dir}[/]")


def _rename_root_directory(
    plugin_dir: Path,
    original_name: str,
    new_name: str,
    console: Console
) -> None:
    """Rename the plugin's root directory."""
    parent_dir = plugin_dir.parent
    new_dir = parent_dir / new_name
    
    if plugin_dir.exists() and plugin_dir != new_dir:
        plugin_dir.rename(new_dir)
        console.print(f"  Renamed directory: {plugin_dir.name} -> {new_dir.name}")