#!/usr/bin/env bash
#
# install.sh — install the sw-build CLI from this repository.
#
# The tool reads its configuration from this repository's .env
# (config.PROJECT_ROOT = <package>/..), so it must stay an editable install:
# the script creates/updates ./.venv, installs the project with `-e`, and puts
# a `sw-build` launcher on PATH. A copy or a non-editable install would move
# the package into another site-packages tree and lose the .env lookup.
#
# Exit status:
#   0    installed successfully, or a completed --dry-run
#   1    missing dependency, failed install, or a failed smoke test
#   2    usage error (bad or missing option value)
#   130  interrupted with Ctrl-C
#
# Usage:
#   ./scripts/install.sh                 # install to ~/.local/bin
#   ./scripts/install.sh --prefix DIR    # install elsewhere (e.g. /usr/local/bin)
#   ./scripts/install.sh --copy          # copy the launcher instead of symlinking
#   ./scripts/install.sh --no-install    # reuse ./.venv, skip dependency install
#   ./scripts/install.sh --dry-run       # print the plan, change nothing
#
# Environment:
#   PREFIX   install prefix (default: ~/.local/bin)
#   PYTHON   interpreter for the pip fallback (default: python3)

set -euo pipefail
# -e: exit immediately if a command exits with a non-zero status
# -u: treat unset variables as an error
# -o pipefail: return the exit status of the last command in a pipeline that failed

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly APP_NAME="sw-build"
readonly VENV="$REPO_ROOT/.venv"
readonly VENV_PY="$VENV/bin/python"
readonly VENV_BIN="$VENV/bin/$APP_NAME"

MODE="symlink"
DO_INSTALL=1
DRY_RUN=0
QUIET=0
PREFIX="${PREFIX:-$HOME/.local/bin}"

# ---- Output helpers ---------------------------------------------------------

log() {
    [[ $QUIET -eq 1 ]] || printf '==> %s\n' "$*" >&2
}

warn() {
    printf 'warning: %s\n' "$*" >&2
}

die() {
    printf 'error: %s\n' "$2" >&2
    exit "$1"
}

usage() {
    sed -n '/^# install.sh/,/^#   PYTHON/p' "$0" | sed 's/^# \{0,1\}//'
}

# ---- Argument handling ------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h | --help)
            usage
            exit 0
            ;;
        --prefix)
            [[ $# -ge 2 ]] || die 2 "--prefix requires a directory"
            PREFIX="$2"
            shift
            ;;
        --prefix=*)
            PREFIX="${1#*=}"
            ;;
        --symlink)
            MODE="symlink"
            ;;
        --copy)
            MODE="copy"
            ;;
        --no-install)
            DO_INSTALL=0
            ;;
        --dry-run)
            DRY_RUN=1
            ;;
        -q | --quiet)
            QUIET=1
            ;;
        *)
            die 2 "unknown argument: $1 (try --help)"
            ;;
    esac
    shift
done

[[ -n "$PREFIX" ]] || die 2 "--prefix must not be empty"
[[ -f "$REPO_ROOT/pyproject.toml" ]] || die 1 "pyproject.toml not found in $REPO_ROOT"

# ---- Helpers ----------------------------------------------------------------

# Print the version from pyproject.toml, or "unknown".
read_version() {
    local version
    version="$(sed -n 's/^version = "\(.*\)"/\1/p' "$REPO_ROOT/pyproject.toml" | head -n 1)"
    printf '%s\n' "${version:-unknown}"
}

# Create or update the repository virtual environment.
ensure_venv() {
    if command -v uv >/dev/null 2>&1; then
        log "Creating/updating $VENV (uv)"
        uv venv --allow-existing "$VENV"
    else
        local python="${PYTHON:-python3}"
        command -v "$python" >/dev/null 2>&1 \
            || die 1 "$python not found; install uv or set PYTHON"
        if [[ ! -x "$VENV_PY" ]]; then
            log "Creating $VENV ($python)"
            "$python" -m venv "$VENV"
        else
            log "Reusing $VENV"
        fi
    fi
}

# Install the project in editable mode so PROJECT_ROOT stays this repo.
install_project() {
    if command -v uv >/dev/null 2>&1; then
        log "Installing project (editable) with uv"
        uv pip install --python "$VENV_PY" -e "$REPO_ROOT"
    else
        log "Installing project (editable) with pip"
        "$VENV_PY" -m pip install --upgrade pip
        "$VENV_PY" -m pip install -e "$REPO_ROOT"
    fi
}

# Seed .env from the example without ever overwriting an existing file.
ensure_env_file() {
    if [[ -f "$REPO_ROOT/.env" ]]; then
        return 0
    fi
    if [[ -f "$REPO_ROOT/.env.example" ]]; then
        log "Creating $REPO_ROOT/.env from .env.example"
        cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
        warn "edit $REPO_ROOT/.env and set RELEASE_DIR before your first build"
    else
        warn "$REPO_ROOT/.env is missing and no .env.example was found"
    fi
}

# Put the launcher on PATH.
install_launcher() {
    local dst="$PREFIX/$APP_NAME"
    mkdir -p "$PREFIX"

    if [[ "$MODE" == "symlink" ]]; then
        rm -f "$dst"
        ln -s "$VENV_BIN" "$dst"
        log "Symlinked $dst -> $VENV_BIN"
    else
        install -m 0755 "$VENV_BIN" "$dst.tmp.$$"
        mv -f "$dst.tmp.$$" "$dst"
        log "Installed $dst"
    fi
}

# Confirm the launcher actually runs.
smoke_test() {
    local dst="$PREFIX/$APP_NAME"
    if "$dst" --help >/dev/null 2>&1; then
        log "Verified $dst --help"
    else
        die 1 "$dst --help failed; the install is incomplete"
    fi
}

# ---- Plan -------------------------------------------------------------------

VERSION="$(read_version)"
BIN_DST="$PREFIX/$APP_NAME"

{
    printf 'sw-build installer\n\n'
    printf '  Version:      %s\n' "$VERSION"
    printf '  Source:       %s\n' "$REPO_ROOT"
    printf '  Virtualenv:   %s\n' "$VENV"
    printf '  Install mode: %s\n' "$MODE"
    printf '  Destination:  %s\n' "$BIN_DST"
    printf '\nPlanned actions\n'
    if [[ $DO_INSTALL -eq 1 ]]; then
        printf '  1. Create/update .venv and install the project (editable)\n'
    else
        printf '  1. Reuse the existing .venv (--no-install)\n'
    fi
    printf '  2. Seed .env from .env.example if it is missing\n'
    printf '  3. %s %s\n' \
        "$([[ "$MODE" == "symlink" ]] && printf 'Symlink' || printf 'Install')" "$BIN_DST"
    printf '  4. Verify the launcher with `sw-build --help`\n'
    if [[ $DRY_RUN -eq 1 ]]; then
        printf '\nDry run: nothing will be changed.\n'
    fi
} >&2

if [[ $DRY_RUN -eq 1 ]]; then
    exit 0
fi

# ---- Install ----------------------------------------------------------------

trap 'exit 130' INT TERM

if [[ $DO_INSTALL -eq 1 ]]; then
    ensure_venv
    install_project
else
    [[ -x "$VENV_PY" ]] || die 1 "$VENV_PY not found; run without --no-install"
fi

[[ -x "$VENV_BIN" ]] || die 1 "$VENV_BIN not found; the project install did not create the CLI"
ensure_env_file
install_launcher
smoke_test

# ---- Report -----------------------------------------------------------------

case ":$PATH:" in
    *":$PREFIX:"*) ;;
    *)
        warn "$PREFIX is not in your PATH. Add this to your shell profile:"
        warn "  export PATH=\"$PREFIX:\$PATH\""
        ;;
esac

printf '\nsw-build %s installed at %s\n' "$VERSION" "$BIN_DST"
