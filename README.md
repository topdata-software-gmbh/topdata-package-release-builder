# Topdata Package Release Builder

## About

The Topdata Package Release Builder (`sw-build`) is a command-line tool designed to automate the process of building and packaging Shopware 6 plugins. It streamlines the entire release workflow, handling versioning, file exclusion, dependency injection, creation of plugin variants, and optional deployment steps like remote synchronization and Slack notifications.

For detailed instructions on installation, configuration, and usage, please see the full user guide in the `manual/` directory.

## Key Features

- **Automated Packaging:** Creates release-ready ZIP archives of Shopware 6 plugins.
- **Intelligent File Exclusion:** Excludes development files using a built-in pattern list plus a custom `.sw-zip-blacklist` file.
- **Interactive & Automated Versioning:** Bumps the plugin version in `composer.json`, and automatically commits and tags the change in Git. Can be controlled via interactive prompt or CLI flags.
- **Foundation Code Injection:** Automatically detects if `TopdataFoundationSW6` is a dependency and injects the necessary code, making the plugin self-contained.
- **Plugin Variant Creation:** Generates renamed variants of a plugin (e.g., a "Free" version) by transforming namespaces, metadata, and class names using `--variant-prefix` and `--variant-suffix` flags.
- **Main-Free Branch Publishing:** Opt-in `.topdata/build.yaml` manifest publishes a self-contained `Free<PluginName>` variant to an append-only `main-free` branch, so shop installations update with a plain `git pull`.
- **Asset Verification:** Verifies compiled storefront and administration assets (JS/CSS) against their sources by SHA-256 content hash, so a release cannot ship stale or entirely missing compiled output.
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

## Free Branch Publishing

Add a committed `.topdata/build.yaml` to opt a plugin into free branch publishing:

```yaml
free:                 # empty mapping means: enabled with defaults
  branch: main-free   # optional, default "main-free"
  zip: false          # optional, default false
```

On every build the tool publishes `Free<PluginName>` to `origin/<branch>`:

- The first snapshot is an orphan commit containing the complete plugin at the branch root.
- Later snapshots append exactly one commit on top of the published tip, so a shop clone
  updates with `git pull` only; published history is never rewritten and no force-push is used.
- The tree is the release payload (same exclusions as the ZIP) plus `.topdata`, renamed and,
  when the plugin requires `topdata/topdata-foundation-sw6`, with the foundation code injected.
- A build whose content is unchanged (including only a new `Created` timestamp in
  `release_info.txt`) adds no commit.
- Free work requires a clean working tree; uncommitted changes abort the build before paid
  uploads or notifications. `--skip-free` is the only bypass and prints a warning.
- `zip: true` additionally creates `<FreePluginName>-v<version>.zip` and follows the normal
  upload/notification path. `--no-sync` keeps that archive local but never suppresses the branch.
- Without a manifest, builds behave exactly as before.
