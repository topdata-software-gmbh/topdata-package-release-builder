"""Release information handling module."""
from datetime import datetime
from typing import Any

import pytz
from topdata_package_release_builder.table import create_table

#: Row labels the consuming package-service is able to parse out of this file.
#: ``table_style="default"`` is required for them to be readable -- the
#: borderless style has no ``:``/``|`` separator, so its rows do not match the
#: consumer's regex and every value is silently lost.
PARSED_LABELS = ("Created", "Branch", "Commit ID")


def _asset_rows(assets: dict[str, Any] | None) -> list[list[str]]:
    """Build the asset-provenance rows for the release record.

    Returns nothing when no verification result was supplied, so a
    human-facing message (the Slack notification) never asserts an asset
    state it has not actually checked.
    """
    if not assets:
        return []

    targets = assets.get("targets") or {}
    if not targets:
        # Nothing was compiled, so toolchain state is not applicable and
        # asserting "Node: n/a" would be misleading noise.
        return [["Assets", "none compiled"]]

    summary = ", ".join(sorted(targets))
    toolchain = assets.get("toolchain") or {}
    node = toolchain.get("node") or "n/a"
    lockfile = toolchain.get("lockfile") or None
    lock_label = (
        f"{lockfile['name']}:{lockfile['sha256'][:12]}" if lockfile else "none"
    )

    return [
        ["Assets", summary],
        ["Node", node],
        ["Lockfile", lock_label],
    ]


def create_release_info(
    plugin_name: str,
    branch: str,
    commitId: str,
    version: str,
    verbose: bool = False,
    console: Any = None,
    table_style: str = "default",
    assets: dict[str, Any] | None = None,
) -> str:
    """Create a plain-text release_info.txt with formatted content.

    Args:
        plugin_name: Name of the plugin
        branch: Branch name
        commitId: Commit ID
        version: Version number
        verbose: Enable verbose output
        console: Console object for output
        table_style: Table style - "default" (with column separators) or
            "simple" (borderless). Only "default" is machine-readable; use it
            for anything written into the release ZIP.
        assets: Optional asset-verification result (see :mod:`.assets`) whose
            provenance is recorded alongside the git provenance.
    """
    if verbose and console:
        console.print("[dim]→ Generating release info with timezone: Europe/Berlin[/]")
    now = datetime.now(pytz.timezone('Europe/Berlin')).strftime('%Y-%m-%d %H:%M')

    if verbose and console:
        console.print("[dim]→ Collecting release info data[/]")
    data = [
        ["Plugin", plugin_name],
        ["Version", f"v{version}"],
        ["Created", now],
        ["Branch", branch],
        ["Commit ID", commitId],
    ]
    data.extend(_asset_rows(assets))

    if verbose and console:
        console.print("[dim]→ Release info data collected:[/]")
        for key, value in data:
            console.print(f"[dim]  • {key}: {value}[/]")
        console.print("[dim]→ Generating formatted table[/]")

    table = create_table(data, style=table_style)

    if verbose and console:
        console.print("[dim]→ Release info table generated[/]")

    return table