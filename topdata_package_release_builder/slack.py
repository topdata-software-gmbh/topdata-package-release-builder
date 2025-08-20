"""Slack notification module for plugin releases."""
import json
import os
from typing import Dict, Optional

import requests
from .release import create_release_info
from rich.console import Console

def send_release_notification(
    plugin_name: str,
    version: str,
    branch: str,
    commit: str,
    download_url: str,
    webhook_url: str,
    variant_info: Optional[Dict] = None,  # Add this parameter
    verbose: bool = False,
    console: Console = None
) -> bool:
    """Send a notification to Slack about the new plugin release."""
    if not webhook_url:
        if console:
            console.print("[yellow]Warning:[/] No Slack webhook URL provided")
        return False

    header_text = f"🚀 New Plugin Release: {plugin_name} v{version}"
    if variant_info:
        header_text = f"🚀 New Plugin Release & Variant for: {plugin_name} v{version}"

    # Main package info
    main_package_info = create_release_info(
        plugin_name, branch, commit, version, verbose, console, table_style="panel"
    )

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Main Package:*\n```{main_package_info}```"
                }
            }
        ]
    }

    if download_url:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Download:*\n{download_url}"
            }
        })
    
    # --- Add Variant Info if it exists ---
    if variant_info and variant_info.get('name'):
        variant_name = variant_info['name']
        variant_download_url = variant_info.get('download_url')
        
        variant_package_info = create_release_info(
            variant_name, branch, commit, version, verbose, console, table_style="panel"
        )

        message["blocks"].append({"type": "divider"})
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Variant Package:*\n```{variant_package_info}```"
            }
        })

        if variant_download_url:
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Download Variant:*\n{variant_download_url}"
                }
            })

    try:
        if verbose and console:
            console.print(f"[dim]→ Sending Slack notification to webhook...[/]")
            
        response = requests.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if verbose and console:
            console.print(f"[dim]→ Slack API response status: {response.status_code}[/]")
            
        response.raise_for_status()
        
        if verbose and console:
            console.print("[dim]→ Slack notification sent successfully[/]")
        return True

    except requests.exceptions.RequestException as e:
        if console:
            console.print(f"[yellow]Warning:[/] Failed to send Slack notification: {str(e)}")
            if verbose:
                console.print(f"[dim]→ Full error: {repr(e)}[/]")
        return False
