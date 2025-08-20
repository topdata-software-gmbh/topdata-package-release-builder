--- 
title: Configuration
---
# Configuration

The `sw-build` tool is configured via environment variables defined in an `.env` file located in the project's root directory.

### Core Settings

| Variable      | Required | Description                                                                                                                                                                                             | Example                                            |
|---------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------|
| `RELEASE_DIR` | **Yes**  | The absolute path to the local directory where the final ZIP archives of the plugins will be stored. The tool will create this directory if it does not exist.                                             | `/home/user/shopware-releases`                     |
| `MANUALS_DIR` | No       | The absolute path to a local clone of a central Git repository for manuals. If set, the tool will copy the plugin's `manual/` folder here, commit, and push the changes.                                  | `/home/user/development/sw6-plugin-manuals`        |

### Remote Sync (rsync)

These settings are required if you want to use the automatic remote sync feature.

| Variable                          | Required | Description                                                                                                                               | Example                                              |
|-----------------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| `RSYNC_SSH_HOST`                  | No       | The SSH host for the remote server, including the username.                                                                               | `user@your-server.com`                               |
| `RSYNC_SSH_PORT`                  | No       | The SSH port for the remote server. Defaults to `22`.                                                                                     | `2222`                                               |
| `RSYNC_REMOTE_PATH_RELEASES_FOLDER` | No       | The base path on the remote server where plugin releases should be stored. The tool will automatically create a subdirectory for each plugin. | `/var/www/releases/`                                 |

### Notifications (Slack)

These settings are used for sending release notifications.

| Variable            | Required | Description                                                                                                                            | Example                                                            |
|---------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| `SLACK_WEBHOOK_URL` | No       | The full incoming webhook URL provided by Slack to post messages to a specific channel.                                                  | `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX` |
| `DOWNLOAD_BASE_URL` | No       | A public base URL used to construct a download link for the synced ZIP file. This link is included in the Slack notification for convenience. | `https://downloads.example.com/plugins`                 |

### Advanced Settings

| Variable                      | Required | Description                                                                                                                                                                | Example                                                    |
|-------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| `FOUNDATION_PLUGIN_PATH`      | No       | The absolute path to your local checkout of the `topdata-foundation-sw6` plugin. This is required for the foundation injection feature.                                    | `/home/user/development/topdata-foundation-sw6`            |
| `DOCS_GENERATOR_PROJECT_PATH` | No       | The absolute path to a documentation generator project. If set, a helpful reminder to run the generator will be displayed in the final success message after a build. | `/home/user/development/docs-generator`                    |
