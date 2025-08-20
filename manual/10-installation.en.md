--- 
title: Installation
---
# Installation Guide

Follow these steps to install the `sw-build` tool on your local development machine.

## Prerequisites

- Python 3.8 or newer.
- `git` installed and available in your system's PATH.
- `uv` (recommended) or `pip` for Python package management.
- `rsync` (required for the remote sync feature).
- (Optional) `pandoc` with a LaTeX engine like `xelatex` if you intend to use the included `pdf.py` script for generating PDF manuals.

## Step 1: Clone the Repository

First, clone the project from its Git repository to a location on your machine.

```bash
git clone git@github.com:topdata-software-gmbh/topdata-package-release-builder.git
cd topdata-package-release-builder
```

## Step 2: Set Up a Virtual Environment

It is highly recommended to use a virtual environment to isolate the tool's dependencies.

```bash
# Create the virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate
```
You will need to activate the environment in each new terminal session before using the `sw-build` command.

## Step 3: Install Dependencies

Install the required Python packages using `uv`. The `-e` flag installs the project in "editable" mode, which is convenient for development.

```bash
uv pip install -e .
```

## Step 4: Create Configuration File

The tool is configured using an `.env` file in its root directory. Copy the example file to create your own local configuration.

```bash
cp .env.example .env
```
Now, open the `.env` file in a text editor. **At a minimum, you must set the `RELEASE_DIR` variable.** This is the directory where all built plugin packages will be saved.

See the [Configuration](./30-configuration.en.md) chapter for details on all available settings.

## Step 5: Verify Installation

You can verify that the tool was installed correctly by running the help command:

```bash
sw-build --help
```

If the installation was successful, you will see a list of all available commands and options. You are now ready to use the tool.
