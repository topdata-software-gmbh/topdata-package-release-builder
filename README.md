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

### Automatic Manual/Documentation Publishing
The builder can automatically publish a plugin's documentation to a central location during the release process. This is useful for keeping a centralized documentation repository up-to-date with each new plugin version.

**How it works:**

1.  **Plugin Structure:** Your plugin must contain a `manual/` directory in its root. This directory should contain all documentation files (e.g., Markdown files, images).
2.  **Configuration:** In your `.env` file, set the `MANUALS_DIR` variable to the absolute path of your central documentation directory.
    ```dotenv
    # in .env file
    MANUALS_DIR=/path/to/your/central/docs/repo
    ```
3.  **Process:** When you run `sw-build`, after the plugin ZIP archive is successfully created, the tool will:
    *   Check if `MANUALS_DIR` is configured.
    *   If it is, it will copy the entire contents of your plugin's `manual/` directory to a versioned sub-folder in the destination.

**Example:**
- If you build version `1.2.3` of a plugin named `MyAwesomePlugin`.
- And your `MANUALS_DIR` is set to `/docs/plugins`.
- The documentation will be copied to `/docs/plugins/MyAwesomePlugin/v1.2.3/`.


## TODO
- when creating a release zip, log it somewhere (release-log-path should be part of the config file)
- 