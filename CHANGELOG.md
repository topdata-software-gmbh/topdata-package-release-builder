# Changelog

## Unreleased

### Added
- `sw-build free enable|disable|status` subcommands to manage the `.topdata/build.yaml`
  free-branch opt-in without hand-editing YAML.
- `scripts/install.sh` to create the editable `.venv`, seed `.env`, link `sw-build` onto
  PATH, and smoke-test the result (`--prefix`, `--copy`, `--no-install`, `--dry-run`).
