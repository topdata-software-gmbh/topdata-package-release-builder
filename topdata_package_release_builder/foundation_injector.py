# File: topdata_package_release_builder/foundation_injector.py

"""Foundation plugin injection utilities.

This module provides the :func:`inject_foundation_code` helper that copies the
relevant **TopdataFoundationSW6** source-code into a *target* plugin build
folder so that the final ZIP becomes **self-contained**.

This version implements an advanced, multi-pass "tree-shaking" mechanism:
1. It analyzes the target plugin for all `use` statements of foundation classes.
2. It recursively analyzes those foundation files for their own dependencies,
   building a complete dependency graph.
3. It specifically includes framework-required classes (like EntityDefinitions)
   that might not be directly `use`d.
4. It copies only the PHP files for the final, required set of classes.
5. It injects only the corresponding service definitions, rewriting their IDs
   to match the new namespace.
6. Finally, it rewrites all namespaces in PHP files to ensure consistency.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, Set
from xml.dom.minidom import Document, Element, parse

OLD_NAMESPACE_BASE = 'Topdata\\TopdataFoundationSW6'


def _fqcn_to_path(fqcn: str, ns_base: str, src_root: Path) -> Path | None:
    """Converts a Fully Qualified Class Name to a file path, if it exists."""
    if not fqcn.startswith(ns_base):
        return None

    relative_path_str = fqcn.removeprefix(ns_base).replace('\\', '/')
    file_path = src_root / f"{relative_path_str.strip('/')}.php"
    return file_path if file_path.exists() else None


def _perform_tree_shaking_and_injection(
        target_plugin_build_dir: Path,
        foundation_plugin_path: Path,
        old_ns_base: str,
        new_ns_base: str,
        target_foundation_dir: Path,
        console=None,
):
    """
    Performs a multi-pass analysis to find all required files, copies them,
    and injects their service definitions with rewritten namespaces.
    """
    foundation_src_path = foundation_plugin_path / 'src'
    use_pattern = re.compile(rf'^use\s+({re.escape(old_ns_base)}\\[\w\\\\]+)(?:\s+as\s+\w+)?;', re.MULTILINE)

    # 1. Load foundation service definitions into a lookup map
    foundation_service_map: Dict[str, Element] = {}
    foundation_services_xml = foundation_plugin_path / 'src/Resources/config/services.xml'
    if foundation_services_xml.exists():
        try:
            doc = parse(str(foundation_services_xml))
            for service_node in doc.getElementsByTagName('service'):
                if fqcn := service_node.getAttribute('id'):
                    foundation_service_map[fqcn] = service_node
        except Exception as e:
            if console:
                console.print(f"[yellow]Warning:[/] Could not parse foundation services.xml: {e}")

    # 2. Seed the initial list of required classes from the target plugin
    if console:
        console.print("[dim]→ Scanning plugin for initial dependencies...[/dim]")

    pending_classes_to_check: Set[str] = set()
    for php_file in target_plugin_build_dir.glob('**/*.php'):
        try:
            content = php_file.read_text(encoding='utf-8')
            for fqcn in use_pattern.findall(content):
                pending_classes_to_check.add(fqcn)
        except Exception:
            pass

    if console:
        console.print(f"[dim]→ Found {len(pending_classes_to_check)} initial dependencies.[/dim]")

    # 3. Recursively resolve all dependencies
    if console:
        console.print("[dim]→ Resolving dependency graph...[/dim]")

    final_classes_to_include: Set[str] = set()
    checked_classes: Set[str] = set()

    while pending_classes_to_check:
        fqcn = pending_classes_to_check.pop()
        if fqcn in checked_classes:
            continue

        checked_classes.add(fqcn)
        final_classes_to_include.add(fqcn)

        if not (source_file := _fqcn_to_path(fqcn, old_ns_base, foundation_src_path)):
            continue

        try:
            content = source_file.read_text(encoding='utf-8')
            for new_dependency_fqcn in use_pattern.findall(content):
                if new_dependency_fqcn not in checked_classes:
                    pending_classes_to_check.add(new_dependency_fqcn)
        except Exception:
            pass

    # 4. Add "soft" dependencies (e.g., EntityDefinitions tagged in services.xml)
    for fqcn, service_node in foundation_service_map.items():
        for tag_node in service_node.getElementsByTagName('tag'):
            if tag_node.getAttribute('name') == 'shopware.entity.definition':
                if fqcn not in final_classes_to_include:
                    if console:
                        console.print(
                            f"[dim]  → Found soft dependency (EntityDefinition): [cyan]{Path(fqcn).name}[/cyan][/dim]")
                    final_classes_to_include.add(fqcn)
                break

    if console:
        console.print(f"[dim]→ Found {len(final_classes_to_include)} total required foundation classes.[/dim]")

    # 5. Copy all required PHP files
    for fqcn in final_classes_to_include:
        if source_file := _fqcn_to_path(fqcn, old_ns_base, foundation_src_path):
            relative_path = source_file.relative_to(foundation_src_path)
            dest_file_path = target_foundation_dir / relative_path
            dest_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest_file_path)

    # 6. Inject required service definitions into target's services.xml
    target_services_xml = target_plugin_build_dir / 'src/Resources/config/services.xml'
    if not target_services_xml.exists():
        if console:
            console.print("[yellow]Warning:[/] Target services.xml not found. Skipping service injection.")
        return

    try:
        target_doc = parse(str(target_services_xml))
        target_services_node = target_doc.getElementsByTagName('services')[0]

        services_injected = 0
        for fqcn in sorted(list(final_classes_to_include)):
            if fqcn in foundation_service_map:
                service_node = foundation_service_map[fqcn].cloneNode(deep=True)

                original_id = service_node.getAttribute('id')
                new_id = original_id.replace(old_ns_base, new_ns_base)
                service_node.setAttribute('id', new_id)

                imported_node = target_doc.importNode(service_node, True)
                target_services_node.appendChild(imported_node)
                services_injected += 1

        if services_injected > 0:
            with open(target_services_xml, 'w', encoding='utf-8') as f:
                xml_content = target_doc.toprettyxml(indent="    ", encoding="UTF-8").decode('utf-8')
                xml_content_cleaned = "\n".join([line for line in xml_content.split('\n') if line.strip()])
                f.write(xml_content_cleaned)
            if console:
                console.print(f"[dim]→ Injected and rewrote {services_injected} required service definitions.[/dim]")

    except Exception as e:
        if console:
            console.print(f"[bold red]Error processing services.xml: {e}[/]")


def inject_foundation_code(
        target_plugin_build_dir: str | Path,
        foundation_plugin_path: str | Path,
        *,
        console=None,
) -> None:
    target_plugin_build_dir = Path(target_plugin_build_dir)
    foundation_plugin_path = Path(foundation_plugin_path)

    # 1. Sanity checks and composer.json patching
    composer_json_path = target_plugin_build_dir / 'composer.json'
    if not composer_json_path.is_file():
        raise FileNotFoundError(f"composer.json not found in {target_plugin_build_dir}")

    if console:
        console.print("[dim]→ Loading and patching composer.json...[/dim]")
    composer_data = json.loads(composer_json_path.read_text(encoding='utf-8'))
    if 'require' in composer_data and 'topdata/topdata-foundation-sw6' in composer_data['require']:
        del composer_data['require']['topdata/topdata-foundation-sw6']

    plugin_class: str = composer_data['extra']['shopware-plugin-class']
    target_namespace_base = "\\".join(plugin_class.split('\\')[:-1])
    new_namespace_base = f"{target_namespace_base}\\Foundation"
    composer_data.setdefault('autoload', {}).setdefault('psr-4', {})[f"{new_namespace_base}\\"] = "src/Foundation/"
    composer_json_path.write_text(json.dumps(composer_data, indent=4) + "\n", encoding='utf-8')

    # 2. Perform tree-shaking, file copying, and service injection
    target_foundation_dir = target_plugin_build_dir / 'src' / 'Foundation'
    target_foundation_dir.mkdir(parents=True, exist_ok=True)
    _perform_tree_shaking_and_injection(
        target_plugin_build_dir,
        foundation_plugin_path,
        OLD_NAMESPACE_BASE,
        new_namespace_base,
        target_foundation_dir,
        console
    )

    # 3. Rewrite namespaces in all files (copied and original)
    if console:
        console.print(f"[dim]→ Rewriting all namespaces from '{OLD_NAMESPACE_BASE}' to '{new_namespace_base}'...[/dim]")
    files_rewritten = rewrite_namespaces_in_dir(target_plugin_build_dir, OLD_NAMESPACE_BASE, new_namespace_base)
    if console:
        console.print(f"[dim]→ Rewrote namespaces in {files_rewritten} total files.[/dim]")
        console.print("[green]✓ Foundation code injected and services registered successfully.[/green]")


def rewrite_namespaces_in_dir(directory: Path, old_base: str, new_base: str) -> int:
    """Recursively finds .php files and replaces all occurrences of a namespace."""
    count = 0
    for php_file in directory.glob('**/*.php'):
        try:
            content = php_file.read_text(encoding='utf-8')
            new_content = content.replace(old_base, new_base)
            if new_content != content:
                php_file.write_text(new_content, encoding='utf-8')
                count += 1
        except Exception as e:
            print(f"Warning: Could not process file {php_file}: {e}")
    return count