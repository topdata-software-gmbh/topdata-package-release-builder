# Project Summary: Topdata Package Release Builder

## 1. Project Description & Purpose

This project provides a command-line tool (`sw-build`) designed to automate the process of building and packaging "topdata packages," with a specific focus on creating release-ready ZIP archives for Shopware 6 plugins. It streamlines the release workflow by handling versioning, file inclusion/exclusion, and optional deployment steps.

The tool was created in October 2024.

## 2. Key Features

*   **CLI Interface:** Uses `sw-build` command (built with `click`) for easy interaction.
*   **Automated Packaging:** Creates ZIP archives containing necessary plugin files.
*   **File Exclusion:** Automatically excludes files based on `.gitignore` rules found in directories and a specific `.sw-zip-blacklist` file in the plugin root. Some common development patterns are also hardcoded for exclusion.
*   **Versioning:**
    *   Reads the current version from `composer.json`.
    *   Prompts the user (via `InquirerPy`) to select a version bump type (major, minor, patch, none).
    *   Updates the version in `composer.json` if a bump is selected.
*   **Release Information:** Generates a `release_info.txt` file within the package, containing details like plugin name, version, branch, and commit hash.
*   **Configuration:** Uses a `.env` file in the project root for configuration (release directory, remote server details, Slack webhook, etc.).
*   **Optional Remote Sync:** Can automatically sync the built package to a remote server using `rsync` if configured in `.env`.
*   **Optional Slack Notifications:** Can send a notification to a configured Slack channel upon successful build and sync, including a download link if available.
*   **Optional Manuals Copying:** Can copy associated manuals from a configured directory (`MANUALS_DIR`) into the release structure.

## 3. Architecture & Implementation Details

*   **Language:** Python (3.10+)
*   **Core Frameworks/Libraries:**
    *   `click`: For building the command-line interface.
    *   `python-dotenv`: For loading configuration from the `.env` file.
    *   `rich`: For enhanced terminal output (colors, panels, status indicators).
    *   `InquirerPy`: For interactive prompts (version selection).
*   **Project Structure:**
    *   Modular design with functionalities separated into different Python modules within the `topdata_package_release_builder` package.
    *   Main entry point: `cli.py`.
    *   Configuration loading: `config.py`.
    *   Core logic modules:
        *   `git.py`: Fetches Git information (branch, commit).
        *   `plugin.py`: Reads plugin metadata (`composer.json`), copies necessary files, creates the archive.
        *   `version.py`: Handles version detection, bumping, and updating.
        *   `release.py`: Generates the release information summary.
        *   `remote.py`: Handles `rsync` operations.
        *   `slack.py`: Sends Slack notifications.
        *   `manual.py`: Copies manual files.
        *   `pdf.py`, `table.py`, `tree.py`: Utility modules likely used for formatting or specific tasks (details not fully explored).
*   **Configuration (`.env`):**
    *   `RELEASE_DIR`: (Required) Local directory to store built packages.
    *   `MANUALS_DIR`: (Optional) Directory containing manuals to be copied.
    *   `RSYNC_SSH_HOST`, `RSYNC_SSH_PORT`, `RSYNC_REMOTE_PATH_RELEASES_FOLDER`: (Optional) Details for remote server sync.
    *   `SLACK_WEBHOOK_URL`: (Optional) Webhook URL for Slack notifications.
    *   `DOWNLOAD_BASE_URL`: (Optional) Base URL used to construct download links for Slack notifications.

## 4. Coding Standards & Conventions

*   **Python Version:** 3.10+
*   **Style:** Follows PEP8 (style) and PEP257 (docstrings).
*   **Type Hints:** Mandatory for function signatures.
*   **Naming:** `snake_case` for functions/variables, `PascalCase` for classes.
*   **Formatting:** F-strings preferred.
*   **Modularity:** Code is organized into logical modules.
*   **Comments:** Section comments (`# ----`) used to explain key code blocks.

## 5. Target Audience

This summary is intended for AI agents requiring context about the `topdata-package-release-builder` project to assist with development, maintenance, or analysis tasks.