--- 
title: Usage Guide
---
# Usage Guide

This section covers the practical use of the `sw-build` command, its options, and its main features.

## Basic Build Process

The simplest way to use the tool is to navigate to the root directory of the Shopware 6 plugin you wish to package and run the command without any arguments.

```bash
cd /path/to/your/plugin
sw-build
```

This will trigger the following process:
1.  Check for uncommitted Git changes and ask to stage them.
2.  Verify compiled JS/CSS assets against their sources by content hash (see [Asset Verification](#asset-verification)).
3.  Read `composer.json` to get the plugin name and current version.
4.  Present an interactive prompt to choose a version increment (Major, Minor, Patch, or None).
5.  If a version bump is selected, update `composer.json`, commit the change, create a Git tag, and push both to the remote.
6.  Copy all necessary plugin files to a temporary directory, excluding the built-in development patterns and everything listed in `.sw-zip-blacklist`.
7.  Create a `release_info.txt` file inside the package.
8.  Create the final ZIP archive in the `RELEASE_DIR` defined in your `.env` file.
9.  Execute optional post-build steps like manual publishing, remote sync, and Slack notifications if configured.

## Command-Line Options

The build process can be customized with the following options:

| Option                 | Description                                                                                                 |
|------------------------|-------------------------------------------------------------------------------------------------------------|
| `--output-dir <path>`  | Overrides the `RELEASE_DIR` from your `.env` file, saving the package to the specified path.                  |
| `--source-dir <path>`  | Specifies the plugin source directory. Defaults to the current directory (`.`).                               |
| `--no-sync`            | Disables syncing the package to the remote server, even if rsync is configured in `.env`.                     |
| `-s`, `--notify-slack` | Sends a notification to the configured Slack channel after a successful build and sync.                     |
| `--version-increment`  | Skips the interactive version prompt. Must be one of `none`, `patch`, `minor`, `major`.                       |
| `--variant-prefix <str>`| Creates a renamed variant of the plugin with the given prefix (e.g., "Free").                               |
| `--variant-suffix <str>`| Creates a renamed variant of the plugin with the given suffix (e.g., "Pro").                                |
| `--with-foundation`    | Forces the injection of `TopdataFoundationSW6` code, regardless of the `composer.json` dependency.          |
| `-v`, `--verbose`      | Enables detailed, step-by-step output of the build process for debugging.                                   |
| `--require-compiled-assets` | Aborts the build when an asset target has sources but no compiled output. Off by default because most Topdata plugins ship hand-written Twig/CSS with no build step. |
| `--debug`              | Enables extra debug output, particularly for asset verification (prints the content digests behind each decision). |

### Example

To build a patch release of a plugin, create a "Free" variant, and notify Slack, without being prompted interactively:

```bash
sw-build --version-increment patch --variant-prefix Free --notify-slack
```

## Key Features in Detail

### File Exclusion

The tool automatically excludes files that are not meant for a production release. The exclusion rules are sourced from:
1.  A hardcoded list of common development patterns (e.g., `.git`, `node_modules`, `tests`).
2.  A `.sw-zip-blacklist` file in the root of your plugin. Each line in this file is treated as a pattern for exclusion. Comments can be added with `#`.

> **Note:** `.gitignore` files are **not** consulted. Compiled output under `src/Resources/public/` is usually gitignored, and honouring `.gitignore` would strip exactly those files from the package. Use `.sw-zip-blacklist` to exclude additional paths.

### Asset Verification

Compiled assets are verified by **SHA-256 content hash**, not by file timestamp. A clone, pull or rsync rewrites modification times, so a timestamp comparison gives an arbitrary answer for exactly the checkouts that were never compiled by hand.

Three asset targets are checked, each pairing a source directory with the output it should produce:

| Target | Sources | Compiled output |
|---|---|---|
| Administration JS | `src/Resources/app/administration/src` (`*.ts`, `*.js`) | `src/Resources/public/administration/js` |
| Storefront JS | `src/Resources/app/storefront/src` (`*.ts`, `*.js`) | `src/Resources/public/storefront/js` |
| Storefront CSS | `src/Resources/app/storefront/src` (`*.scss`, `*.css`) | `src/Resources/public/storefront/css` |

A target with sources but **no** compiled output is:

- an **error** if the plugin already ships any compiled asset (so a plugin that compiles must compile every side it has sources for), or if `--require-compiled-assets` is passed;
- a **warning** otherwise — most Topdata plugins have hand-written `.js`/`.scss` under `Resources/app` and no build step at all, and blocking their release would be wrong.

After a **successful** verification the source and output digests are recorded in `.git/sw-build/<plugin>/.sw-build-assets.json`. This manifest is **local state**: it lives inside the git directory, so it never reaches the release ZIP, is never seen by `git status`, and cannot conflict with another developer's checkout. A first build in a fresh checkout records a baseline; every later build in that same checkout is checked against it, and editing an asset source without recompiling aborts the release. A **failed** verification leaves the previous baseline untouched, so an ignored error can never bless stale output.

The record written into `release_info.txt` and shipped in the ZIP also reports the asset state, the detected Node version and the lockfile digest.

### Foundation Plugin Injection

If your plugin depends on `topdata/topdata-foundation-sw6`, this tool can automatically embed the required foundation code directly into your plugin's ZIP package. This makes your plugin self-contained and simplifies installation for the end-user.

- **Automatic Mode:** The tool checks your plugin's `composer.json`. If it finds the foundation dependency, injection is enabled automatically.
- **Manual Mode:** You can force injection using the `--with-foundation` flag.

For this feature to work, the `FOUNDATION_PLUGIN_PATH` variable must be set correctly in your `.env` file.

### Creating Renamed Variants

This powerful feature allows you to generate a second, renamed version of your plugin from a single build command. It is ideal for creating "Free" or "Pro" editions of a plugin.

When using `--variant-prefix` or `--variant-suffix`, the tool performs a deep transformation:
- It creates a new plugin name (e.g., `MyPlugin` with prefix `Free` becomes `FreeMyPlugin`).
- It rewrites the PHP namespace (e.g., `Topdata\MyPlugin` becomes `Topdata\FreeMyPlugin`).
- It updates the plugin's FQCN (Fully Qualified Class Name).
- It modifies labels and descriptions in `composer.json` to include the variant marker (e.g., `[FREE] My Plugin`).
- It renames the main plugin PHP file.
- It performs a global find-and-replace for the old name and namespace across all PHP, XML, Twig, and JS files.

The original plugin is always built alongside the variant. Both ZIP files will be placed in the release directory.
