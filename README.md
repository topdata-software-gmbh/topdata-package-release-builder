# Topdata Package Release Builder

## About
- A tool for building and packaging topdata packages (eg shopware6 plugin release zips)
- 10/2024 created

## Installation

1. Clone the repository
```
git clone git@github.com:topdata-software-gmbh/topdata-package-release-builder.git
```

2. Create a virtual environment:
```bash
uv venv
source .venv/bin/activate
```
   
3. Install dependencies:
```bash
# pandoc for PDF generation
pacman -Syu pandoc texlive-xetex texlive-core texlive-formatsextra texlive-latexextra
# python dependencies
uv pip install -e ".[dev]"
```

4. Copy the example environment file and configure it:
```bash
cp .env.example .env
```
Edit `.env` and set at least the required `RELEASE_DIR` value.

5. Test if the installation was successful:
```bash
sw-build --help
```

## Usage

1. Configure your environment:
   - Make sure `RELEASE_DIR` is set in your `.env` file - this is where built packages will be stored
   - Optional: Configure rsync settings for remote syncing
   - Optional: Set up Slack notifications

2. Go to the root directory of the package you want to build and run:
```bash
sw-build --help
```

By default, built packages will be stored in the directory specified by `RELEASE_DIR` in your `.env` file.
You can override this with the `--output-dir` option.

## Features

### File Exclusion
- Some files are hardcoded to be excluded from a release zip (search for `ignored_patterns` in the code).
- The builder makes use of .sw-zip-blacklist in the plugin folder (if found) when creating a release zip.

> ### Automatic Manual/Documentation Publishing
> 
> The builder can automatically publish a plugin's documentation to a central location. If this location is a Git repository, the tool can also automatically commit and push the changes, creating a fully automated documentation pipeline.
> 
> **How it works:**
> 
> 1.  **Central Repository:** You must have a central Git repository to store all your manuals. Clone this repository to your local machine.
> 2.  **Plugin Structure:** Your plugin must contain a `manual/` directory in its root.
> 3.  **Configuration:** In your `.env` file, set the `MANUALS_DIR` variable to the absolute path of your **local clone** of the central documentation repository.
>     ```dotenv
>     # in .env file
>     MANUALS_DIR=/path/to/your/central/docs/repo
>     ```
> 4.  **Process:** When you run `sw-build`, the tool will:
>     *   Check if `MANUALS_DIR` is set.
>     *   Copy the plugin's `manual/` directory into a versioned sub-folder (e.g., `MANUALS_DIR/PluginName/v1.2.3/`).
>     *   **If `MANUALS_DIR` is a Git repository**, it will then automatically perform a `git pull`, `git add`, `git commit`, and `git push` on that repository.

### Foundation Plugin Injection

The builder can automatically inject the TopdataFoundationSW6 plugin code into your plugin packages when needed. This feature is designed to work seamlessly with Shopware 6 plugin dependencies.

**How it works:**

1.  **Automatic Detection:** The builder automatically checks if your plugin declares `TopdataFoundationSW6` as a dependency in its `composer.json` file.
2.  **Smart Injection:** If the dependency is found, the foundation plugin code is automatically injected into the built package.
3.  **Override Option:** You can override the automatic behavior using the `TOPDATA_FORCE_FOUNDATION_INJECTION` environment variable:
    *   Set `TOPDATA_FORCE_FOUNDATION_INJECTION=1` to force injection even if the dependency is not declared.
    *   Set `TOPDATA_FORCE_FOUNDATION_INJECTION=0` to disable injection even if the dependency is declared.
4.  **CLI Flag:** Use the `--with-foundation` flag to force injection regardless of dependency declaration or environment variable settings.

**Usage Examples:**

```bash
# Standard case - injects foundation if dependency is declared
sw-build

# Force injection even without dependency
sw-build --with-foundation

# Override with environment variable
TOPDATA_FORCE_FOUNDATION_INJECTION=1 sw-build
```

### Creating Renamed Variants

The builder supports creating renamed variants of your plugin packages, allowing you to maintain multiple versions with different names for different markets or purposes.

**Purpose:**
- Create free versions of paid plugins by adding "Free" prefix
- Generate branded variants for different clients
- Maintain separate plugin identities for different feature sets
- Support A/B testing with different plugin names

**Usage:**

Use the `--variant-prefix` and/or `--variant-suffix` flags to create renamed variants:

```bash
# Create a free variant with "Free" prefix
sw-build --variant-prefix Free

# Create a branded variant with suffix
sw-build --variant-suffix Pro

# Combine both prefix and suffix
sw-build --variant-prefix Free --variant-suffix Lite

# Create multiple variants in one build
sw-build --variant-prefix Free --variant-suffix Basic --variant-suffix Pro
```

**What gets renamed:**
- Plugin name and description in plugin.xml
- Composer package name and description
- PHP namespace and class names
- Service IDs and configuration keys
- Administration module names and routes
- Storefront template paths

The original plugin package is always built alongside any variants, giving you both the original and renamed versions.

## TODO
- when creating a release zip, log it somewhere (release-log-path should be part of the config file)
- 