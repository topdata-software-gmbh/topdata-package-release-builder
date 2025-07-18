# File: topdata_package_release_builder/foundation_injector.py

"""Foundation plugin injection utilities.

This module provides the :func:`inject_foundation_code` helper that copies the
relevant **TopdataFoundationSW6** source-code into a *target* plugin build
folder so that the final ZIP becomes **self-contained**.

The process works as follows:

1.  Read the target plugin’s ``composer.json`` to determine its base namespace
    and to remove the *external* Composer dependency.
2.  Copy a curated subset of directories from the Foundation plugin into
    ``src/Foundation`` of the target.
3.  Re-write PHP namespaces in the copied files so they live beneath ``<Target>\\Foundation``.
4.  Re-write PHP namespaces in the original plugin files to update all references.
5.  Inject service definitions from the foundation plugin's services.xml into the target's services.xml.
6.  Update ``composer.json`` so the new namespace is autoloaded.

All steps are accompanied by *Rich* console output so the user can follow what
is happening.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional
from xml.dom import minidom

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

# Directories inside the *Foundation* plugin that will be injected.  The list is
# intentionally explicit so that we never ship files that are not required by
# the target plugin.
DIRECTORIES_TO_INJECT: List[str] = [
    'Command',
    'Constants',
    'Core/Content/TopdataReport',
    'DataStructure',
    'DTO',
    'Exception',
    'Helper',
    'Service',
    'Twig',
    'Util',
]

OLD_NAMESPACE_BASE = 'Topdata\\TopdataFoundationSW6'


def inject_foundation_code(
        target_plugin_build_dir: str | Path,
        foundation_plugin_path: str | Path,
        *,
        console=None,
) -> None:
    """Copy Foundation source code *into* the target plugin package.

    Parameters
    ----------
    target_plugin_build_dir:
        Path to the temporary *build* directory of the plugin that is currently
        being packaged (e.g. ``/tmp/abcd/TopdataConnectorSW6``).
    foundation_plugin_path:
        Absolute path to the *source* of the ``TopdataFoundationSW6`` plugin –
        usually configured via the ``FOUNDATION_PLUGIN_PATH`` environment
        variable.
    console:
        Optional :class:`rich.console.Console` instance used for coloured status
        messages.
    """
    target_plugin_build_dir = Path(target_plugin_build_dir)
    foundation_plugin_path = Path(foundation_plugin_path)

    # ------------------------------------------------------------------
    # 1. Sanity checks
    # ------------------------------------------------------------------
    if not foundation_plugin_path.is_dir():
        raise FileNotFoundError(f"Foundation plugin path does not exist: {foundation_plugin_path}")

    composer_json_path = target_plugin_build_dir / 'composer.json'
    if not composer_json_path.is_file():
        raise FileNotFoundError(f"composer.json not found in {target_plugin_build_dir}")

    if console:
        console.print("[dim]→ Loading composer.json from target build directory[/dim]")

    # ------------------------------------------------------------------
    # 2. Read & patch composer.json
    # ------------------------------------------------------------------
    composer_data = json.loads(composer_json_path.read_text(encoding='utf-8'))

    # Remove explicit dependency so the package becomes self-contained.
    if 'require' in composer_data and 'topdata/topdata-foundation-sw6' in composer_data['require']:
        del composer_data['require']['topdata/topdata-foundation-sw6']
        if console:
            console.print(
                "[dim]→ Removed '[bold cyan]topdata/topdata-foundation-sw6[/bold cyan]' from composer requirements.[/dim]")

    # Determine the *target* plugin’s root namespace (e.g. "Topdata\\TopdataConnectorSW6").
    plugin_class: str = composer_data['extra']['shopware-plugin-class']
    target_namespace_base = "\\".join(plugin_class.split('\\')[:-1])

    new_namespace_base = f"{target_namespace_base}\\Foundation"

    # Add PSR-4 autoload rule so the injected classes can be found.
    composer_data.setdefault('autoload', {}).setdefault('psr-4', {})[f"{new_namespace_base}\\"] = "src/Foundation/"

    # Write changes back to disk.
    composer_json_path.write_text(json.dumps(composer_data, indent=4) + "\n", encoding='utf-8')
    if console:
        console.print("[dim]→ composer.json patched with new autoload definition[/dim]")

    # ------------------------------------------------------------------
    # 3. Copy source directories
    # ------------------------------------------------------------------
    target_foundation_dir = target_plugin_build_dir / 'src' / 'Foundation'
    target_foundation_dir.mkdir(parents=True, exist_ok=True)

    for rel_path in DIRECTORIES_TO_INJECT:
        src_dir = foundation_plugin_path / 'src' / rel_path
        dest_dir = target_foundation_dir / rel_path

        if not src_dir.exists():
            if console:
                console.print(f"[yellow]→ Warning:[/] Source directory not found, skipping: {src_dir}")
            continue

        if console:
            console.print(f"[dim]→ Copying [bold]{rel_path}[/] → {dest_dir}[/dim]")

        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)

    # ------------------------------------------------------------------
    # 4. Re-write namespaces in *copied* files
    # ------------------------------------------------------------------
    if console:
        console.print(f"[dim]→ Rewriting namespaces from '{OLD_NAMESPACE_BASE}' to '{new_namespace_base}'[/dim]")

    files_rewritten = rewrite_namespaces_in_dir(target_foundation_dir, OLD_NAMESPACE_BASE, new_namespace_base)

    if console:
        console.print(f"[dim]→ Rewrote namespaces in {files_rewritten} files.[/dim]")

    # ------------------------------------------------------------------
    # 5. Re-write namespaces in the *main plugin* to update references.
    # ------------------------------------------------------------------
    if console:
        console.print(f"[dim]→ Updating references in the main plugin source...[/dim]")

    files_rewritten_in_target = rewrite_namespaces_in_dir(target_plugin_build_dir, OLD_NAMESPACE_BASE,
                                                          new_namespace_base)

    if console:
        console.print(f"[dim]→ Updated references in {files_rewritten_in_target} main plugin files.[/dim]")

    # ------------------------------------------------------------------
    # 6. Inject service definitions from foundation's services.xml
    # ------------------------------------------------------------------
    if console:
        console.print("[dim]→ Injecting service definitions...[/dim]")

    _inject_service_definitions(
        foundation_plugin_path,
        target_plugin_build_dir,
        OLD_NAMESPACE_BASE,
        new_namespace_base,
        console
    )

    if console:
        console.print("[green]✓ Foundation code injected and services registered.[/green]")


def _inject_service_definitions(
        foundation_path: Path,
        target_path: Path,
        old_ns: str,
        new_ns: str,
        console=None
):
    """
    Injects service definitions from the foundation plugin's services.xml
    into the target plugin's services.xml.
    """
    foundation_services_xml = foundation_path / 'src/Resources/config/services.xml'
    target_services_xml = target_path / 'src/Resources/config/services.xml'

    if not foundation_services_xml.exists():
        if console:
            console.print(f"[yellow]→ Warning:[/] Foundation services.xml not found, skipping injection.")
        return
    if not target_services_xml.exists():
        if console:
            console.print(f"[yellow]→ Warning:[/] Target services.xml not found, skipping injection.")
        return

    try:
        # Load foundation and target XML documents
        foundation_doc = minidom.parse(str(foundation_services_xml))
        target_doc = minidom.parse(str(target_services_xml))

        # Get the root <services> element from the target
        target_services_node = target_doc.getElementsByTagName('services')[0]

        # Get all <service> nodes from the foundation XML
        foundation_service_nodes = foundation_doc.getElementsByTagName('service')

        services_injected = 0
        for service_node in foundation_service_nodes:
            original_id = service_node.getAttribute('id')
            if not original_id:
                continue

            # Rewrite the service ID to use the new namespace
            new_id = original_id.replace(old_ns, new_ns, 1)
            service_node.setAttribute('id', new_id)

            # Import the modified node into the target document and append it
            # (importNode is necessary to move nodes between documents)
            imported_node = target_doc.importNode(service_node, True)
            target_services_node.appendChild(imported_node)

            services_injected += 1
            if console:
                console.print(f"[dim]  → Injected service: [cyan]{new_id}[/cyan][/dim]")

        if services_injected > 0:
            # Save the modified XML back to the target file
            with open(target_services_xml, 'w', encoding='utf-8') as f:
                # Use toprettyxml for clean formatting
                xml_content = target_doc.toprettyxml(indent="    ", encoding="UTF-8").decode('utf-8')
                # Remove extra blank lines created by toprettyxml
                xml_content_cleaned = "\n".join([line for line in xml_content.split('\n') if line.strip()])
                f.write(xml_content_cleaned)
            if console:
                console.print(f"[dim]→ Injected {services_injected} service definitions into services.xml.[/dim]")

    except Exception as e:
        if console:
            console.print(f"[bold red]Error processing services.xml: {e}[/]")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def rewrite_namespaces_in_dir(directory: Path, old_base: str, new_base: str) -> int:
    """
    Recursively finds .php files and replaces namespace and use statements.
    Uses simple string replacement which is safer and faster for this task.
    """
    count = 0
    for php_file in directory.glob('**/*.php'):
        try:
            content = php_file.read_text(encoding='utf-8')

            # Use simple, safe string replacement instead of regex.
            # This correctly handles backslashes without misinterpretation.
            new_content = content.replace(old_base, new_base)

            if new_content != content:
                php_file.write_text(new_content, encoding='utf-8')
                count += 1
        except Exception as e:
            # Add some basic error handling in case a file is unreadable
            print(f"Warning: Could not process file {php_file}: {e}")

    return count