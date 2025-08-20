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
2.  Verify that compiled JS/CSS assets are up-to-date.
3.  Read `composer.json` to get the plugin name and current version.
4.  Present an interactive prompt to choose a version increment (Major, Minor, Patch, or None).
5.  If a version bump is selected, update `composer.json`, commit the change, create a Git tag, and push both to the remote.
6.  Copy all necessary plugin files to a temporary directory, excluding files specified in `.sw-zip-blacklist` and `.gitignore`.
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
| `--debug`              | Enables extra debug output, particularly for the timestamp verification of compiled assets.                   |

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
3.  Any `.gitignore` files found within the plugin's directory structure.

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
