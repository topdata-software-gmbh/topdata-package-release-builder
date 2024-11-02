"""Release information handling module."""
from datetime import datetime

import pytz
from topdata_package_release_builder.table import create_table

def create_release_info(plugin_name, branch, commitId, version, verbose=False, console=None, table_style="default"):
    """Create a plain-text release_info.txt with formatted content.

    Args:
        plugin_name: Name of the plugin
        branch: Branch name
        commitId: Commit ID
        version: Version number
        verbose: Enable verbose output
        console: Console object for output
        table_style: Table style - "default" (with dividers) or "simple" (without dividers)
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
        ["Commit ID", commitId]
    ]

    if verbose and console:
        console.print("[dim]→ Release info data collected:[/]")
        for key, value in data:
            console.print(f"[dim]  • {key}: {value}[/]")
        console.print("[dim]→ Generating formatted table[/]")

    table = create_table(data, style=table_style)

    if verbose and console:
        console.print("[dim]→ Release info table generated[/]")

    return table
