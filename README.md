# Topdata Package Release Builder

## About

The Topdata Package Release Builder (`sw-build`) is a command-line tool designed to automate the process of building and packaging Shopware 6 plugins. It streamlines the entire release workflow, handling versioning, file exclusion, dependency injection, creation of plugin variants, and optional deployment steps like remote synchronization and Slack notifications.

For detailed instructions on installation, configuration, and usage, please see the full user guide in the `manual/` directory.

## Key Features

- **Automated Packaging:** Creates release-ready ZIP archives of Shopware 6 plugins.
- **Intelligent File Exclusion:** Excludes development files based on `.gitignore` rules and a custom `.sw-zip-blacklist` file.
- **Interactive & Automated Versioning:** Bumps the plugin version in `composer.json`, and automatically commits and tags the change in Git. Can be controlled via interactive prompt or CLI flags.
- **Foundation Code Injection:** Automatically detects if `TopdataFoundationSW6` is a dependency and injects the necessary code, making the plugin self-contained.
- **Plugin Variant Creation:** Generates renamed variants of a plugin (e.g., a "Free" version) by transforming namespaces, metadata, and class names using `--variant-prefix` and `--variant-suffix` flags.
- **Asset Verification:** Ensures that compiled storefront and administration assets (JS/CSS) are up-to-date before building.
- **Deployment & Notifications:**
    - Optionally syncs the built package to a remote server using `rsync`.
    - Optionally sends a release notification to a Slack channel with a download link.
    - Optionally publishes documentation to a separate Git repository.

## Installation

1.  Clone the repository:
    ```bash
    git clone git@github.com:topdata-software-gmbh/topdata-package-release-builder.git
    cd topdata-package-release-builder
    ```

2.  Create and activate a virtual environment:
    ```bash
    uv venv
    source .venv/bin/activate
    ```
   
3.  Install dependencies:
    ```bash
    uv pip install -e .
    ```

4.  Copy the example environment file and configure it:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and set at least the required `RELEASE_DIR` value.

5.  Test the installation:
    ```bash
    sw-build --help
    ```

## Basic Usage

Navigate to the root directory of the Shopware 6 plugin you want to build and run the command:

```bash
sw-build
```

This will guide you through the versioning process and create the plugin ZIP file in the directory specified by `RELEASE_DIR` in your `.env` file.
