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

## excludes files:
- some files are hardcoded to be excluded from a release zip (search for `ignored_patterns` in the code).
- the builder makes use of .sw-zip-blacklist in the plugin folder (if found) when creating a release zip


## TODO
- when creating a release zip, log it somewhere (release-log-path should be part of the config file)

