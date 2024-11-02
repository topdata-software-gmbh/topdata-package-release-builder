"""Slack notification module for plugin releases."""
import json
import os

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
    verbose: bool = False,
    console: Console = None
) -> bool:
    """Send a notification to Slack about the new plugin release."""
    if not webhook_url:
        if console:
            console.print("[yellow]Warning:[/] No Slack webhook URL provided")
        return False

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚀 New Plugin Release: {plugin_name} v{version}"
                }
            },
            # {
            #     "type": "section",
            #     "fields": [
            #         {
            #             "type": "mrkdwn",
            #             "text": f"*Plugin*:\n{plugin_name}"
            #         },
            #         {
            #             "type": "mrkdwn",
            #             "text": f"*Version:*\nv{version}"
            #         },
            #         {
            #             "type": "mrkdwn",
            #             "text": f"*Branch:*\n{branch}"
            #         }
            #     ]
            # },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```\n{create_release_info(plugin_name, branch, commit, version, verbose, console, table_style="panel")}\n```"
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

    try:
        response = requests.post(
            webhook_url,
            json=message,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        if verbose and console:
            console.print("[dim]→ Slack notification sent successfully[/]")
        return True

    except requests.exceptions.RequestException as e:
        if console:
            console.print(f"[yellow]Warning:[/] Failed to send Slack notification: {str(e)}")
        return False
