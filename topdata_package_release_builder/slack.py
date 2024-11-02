"""Slack notification module for plugin releases."""
import json
import os

import requests
from rich.console import Console

def send_release_notification(
    plugin_name: str,
    version: str,
    branch: str,
    commit: str,
    remote_url: str,
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
                    "text": f"🚀 New Plugin Release: {plugin_name}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Version:*\nv{version}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Branch:*\n{branch}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Commit:*\n`{commit[:8]}`"
                    }
                ]
            }
        ]
    }

    if remote_url:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Download:*\n{remote_url}"
            }
        })

    print(message)

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
