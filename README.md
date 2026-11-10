# Topdata Package Release Builder

## About

The Topdata Package Release Builder (`sw-build`) is a command-line tool designed to automate the process of building and packaging Shopware 6 plugins. It streamlines the entire release workflow, handling versioning, file exclusion, dependency injection, creation of plugin variants, and optional deployment steps like remote synchronization and Slack notifications.

For detailed instructions on installation, configuration, and usage, please see the full user guide in the `manual/` directory.

## Requirements

- Python 3.10+
- Git (required)
- `rsync` (only when remote sync is configured)

## Key Features

- **Automated Packaging:** Creates release-ready ZIP archives of Shopware 6 plugins.
- **Intelligent File Exclusion:** Excludes development files using a built-in pattern list plus a custom `.sw-zip-blacklist` file.
- **Interactive & Automated Versioning:** Bumps the plugin version in `composer.json`, and automatically commits and tags the change in Git. Can be controlled via interactive prompt or CLI flags.
- **Foundation Code Injection:** Automatically detects if `TopdataFoundationSW6` is a dependency and injects the necessary code, making the plugin self-contained.
- **Plugin Variant Creation:** Generates renamed variants of a plugin (e.g., a "Free" version) by transforming namespaces, metadata, and class names using `--variant-prefix` and `--variant-suffix` flags.
- **Main-Free Branch Publishing:** Opt-in `.topdata/build.yaml` manifest publishes a self-contained `Free<PluginName>` variant to an append-only `main-free` branch, so shop installations update with a plain `git pull`.
- **Asset Verification:** Verifies compiled storefront and administration assets (JS/CSS) against their sources by SHA-256 content hash, so a release cannot ship stale or entirely missing compiled output.
- **Self-Upgrade:** `sw-build self-upgrade` pulls the latest code for an editable install and refreshes the package in the same virtualenv; `--force` stashes local changes first.
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
    Edit `.env` and set at least the required `RELEASE_DIR` value. The tool reads this `.env`
    from the repository where it is installed (an editable install is assumed), not from the
    plugin directory you build.

5.  Test the installation:
    ```bash
    sw-build --help
    ```

### Installer script

`./scripts/install.sh` automates the steps above: it creates or updates `./.venv`, installs the
project in editable mode (so the repository `.env` stays the configuration source), seeds `.env`
from `.env.example` if missing, links a `sw-build` launcher onto your PATH, and smoke-tests it.

```bash
./scripts/install.sh                 # install to ~/.local/bin
./scripts/install.sh --prefix DIR    # install elsewhere
./scripts/install.sh --copy          # copy the launcher instead of symlinking
./scripts/install.sh --no-install    # reuse ./.venv, skip dependency install
./scripts/install.sh --dry-run       # print the plan, change nothing
```

The launcher should stay a symlink to `./.venv/bin/sw-build`. Because the install is editable,
`sw-build self-upgrade` can pull new code and refresh dependencies in that same environment.

## Upgrading

For an editable install (including one created by `scripts/install.sh`), update the tool from
its own Git checkout:

```bash
sw-build self-upgrade          # pull latest code and refresh dependencies
sw-build self-upgrade --force  # stash local changes (including untracked) first
```

The command refuses to run on a dirty tree unless `--force` is given, reports when the checkout
is already current, and reinstalls into the interpreter that is running `sw-build` (the `.venv`
launcher from the installer), falling back from `uv` to `pip`. Re-run your command afterwards so
the new code is loaded. A packaged wheel has no upstream to pull and cannot self-upgrade.

## Basic Usage

Navigate to the root directory of the Shopware 6 plugin you want to build and run the command:

```bash
sw-build
```

This will guide you through the versioning process and create the plugin ZIP file in the directory specified by `RELEASE_DIR` in your `.env` file.

> **Version bumps publish automatically.** If you choose a patch/minor/major increment (or pass
> `--version-increment`), `sw-build` updates `composer.json`, then commits, tags, and pushes the
> branch and tag to `origin`. If the working tree is dirty it first asks to `git add .`, so the
> bump commit may include those staged changes.

For the complete option list and feature details, see `manual/40-usage.en.md`.

## Free Branch Publishing

Enable or disable the opt-in from the plugin checkout:

```bash
sw-build free enable                    # writes `.topdata/build.yaml` with `free: {}`
sw-build free enable --branch main-free --zip
sw-build free disable                   # removes the free key
sw-build free status
```

The commands edit a committed file; commit the change yourself.

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

## Development

```bash
uv sync --extra dev                       # project + test/lint tools
uv run --extra dev pytest                 # full test suite
uv run --extra dev pytest tests/test_free_branch.py::test_name
uv run --extra dev ruff check .           # lint
```

Tests build real temporary git repositories (a bare `origin` plus a plugin clone), so
publication behavior is exercised rather than mocked. There is no CI; run pytest and ruff
before committing.
