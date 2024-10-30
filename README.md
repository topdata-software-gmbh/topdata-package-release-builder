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
