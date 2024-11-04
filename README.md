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
uv pip install -e ".[dev]"
```

4. test if the installation was successful:
```bash
 sw-build --help
 ```

## Usage

go to the root directory of the package you want to build and run the following command:
```bash
sw-build --help
```

## excludes files:
- some files are hardcoded to be excluded from a release zip (search for `ignored_patterns` in the code).
- the builder makes use of .sw-zip-blacklist in the plugin folder (if found) when creating a release zip


## TODO
- when creating a release zip, log it somewhere (release-log-path should be part of the config file)

