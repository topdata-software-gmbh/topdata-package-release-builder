# Implementation Plan: Enhance Slack Notifications with Variant Package Details

The goal is to update the Slack notification logic to include details and a download link for the generated variant package, in addition to the main package.

## Phase 1: Modify the Slack Notification Function to Accept Variant Data

The first step is to update the `send_release_notification` function in `slack.py` so it can accept and process information about a variant package.

*   **File to modify:** `topdata_package_release_builder/slack.py`

### Step 1.1: Update the function signature

Modify the function signature of `send_release_notification` to accept an optional dictionary containing the variant's information.

```python
# In topdata_package_release_builder/slack.py

import json
import os
from typing import Dict, Optional # Add Dict and Optional

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
    variant_info: Optional[Dict] = None, # Add this parameter
    verbose: bool = False,
    console: Console = None
) -> bool:
    """Send a notification to Slack about the new plugin release."""
    # ... function body remains for now ...
```

### Step 1.2: Enhance the message construction logic

Update the body of the function to build a more comprehensive message. The new logic will:
1.  Adjust the main header if a variant is present.
2.  Create and add a separate information block for the variant package.
3.  Add the download link for the variant package if it exists.

Replace the existing message construction logic with the following:

```python
# In topdata_package_release_builder/slack.py, inside send_release_notification()

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
        # ... rest of the function (requests.post call) remains the same ...
```

## Phase 2: Update the CLI to Pass Variant Data to the Notification Function

Now that the Slack function is ready to receive variant data, we need to modify the main CLI logic to pass the `variant_info` dictionary when calling it.

*   **File to modify:** `topdata_package_release_builder/cli.py`

### Step 2.1: Locate the call to `send_release_notification`

Find the section in the `build_plugin` function where `send_release_notification` is called. It is located near the end of the function.

### Step 2.2: Add the `variant_info` argument to the function call

Modify the function call to include the `variant_info` dictionary, which is populated during the variant creation process.

**FROM (Original Code):**
```python
# In topdata_package_release_builder/cli.py

            else:
                slack_status = send_release_notification(
                plugin_name=plugin_name,
                version=version,
                branch=branch,
                commit=commit,
                download_url=download_url,  # Using the sync URL as the download link
                webhook_url=webhook_url,
                verbose=verbose,
                console=console
            )
```

**TO (Updated Code):**
```python
# In topdata_package_release_builder/cli.py

            else:
                slack_status = send_release_notification(
                plugin_name=plugin_name,
                version=version,
                branch=branch,
                commit=commit,
                download_url=download_url,  # Using the sync URL as the download link
                webhook_url=webhook_url,
                variant_info=variant_info, # Add this line
                verbose=verbose,
                console=console
            )
```


