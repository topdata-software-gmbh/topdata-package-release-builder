"""Free variant payload assembly and append-only branch publication.

Publication uses low-level git plumbing against the source repository so the
current checkout, index and working tree are never touched. The resulting
branch is fast-forward-only: the first snapshot is an orphan commit and every
later snapshot has exactly one parent, the fetched remote tip.
"""
from __future__ import annotations

import io
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from .foundation_injector import inject_foundation_code
from .plugin import copy_plugin_files
from .release import create_release_info
from .variant import transform_to_variant

FREE_PREFIX = 'Free'
FREE_EXTRA_EXCLUDES = ('.topdata',)

_ROW_RE = re.compile(r'^\s*[│|]\s*(.*?)\s*[│|]\s*(.*?)\s*[│|]\s*$')


class FreePublishError(RuntimeError):
    """Raised when the free payload cannot be published safely."""


@dataclass(frozen=True)
class FreeSnapshot:
    """Result of one publication attempt."""

    branch: str
    version: str
    previous_tip: str | None
    payload_tree: str
    commit: str | None
    committed: bool
    pushed: bool
    timestamp_only: bool = False


def _silent_console() -> Console:
    return Console(file=io.StringIO())


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------


def build_free_payload(
    *,
    source_dir: str | Path,
    plugin_name: str,
    version: str,
    branch: str,
    commit: str,
    foundation_plugin_path: str | Path | None = None,
    assets: dict[str, Any] | None = None,
    console: Console | None = None,
    temp_dir: str | Path | None = None,
) -> tuple[str, Path]:
    """Build the ``Free<plugin>`` payload in a temporary directory.

    Returns ``(free_name, payload_root)``. The caller owns ``temp_dir`` (or the
    directory created here) and is responsible for cleaning it up.
    """
    output_console = console or _silent_console()

    if temp_dir is None:
        temp_path = Path(_make_temp_dir())
    else:
        temp_path = Path(temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True)

    copied_dir = copy_plugin_files(
        str(temp_path),
        plugin_name,
        source_dir=str(source_dir),
        verbose=False,
        console=output_console,
        extra_excludes=FREE_EXTRA_EXCLUDES,
    )

    free_name = transform_to_variant(
        Path(copied_dir),
        plugin_name,
        prefix=FREE_PREFIX,
        suffix='',
        console=output_console,
    )
    payload_root = temp_path / free_name

    if foundation_plugin_path is not None:
        inject_foundation_code(payload_root, foundation_plugin_path, console=output_console)

    release_info = create_release_info(
        free_name,
        branch,
        commit,
        version,
        verbose=False,
        console=output_console,
        assets=assets,
    )
    (payload_root / 'release_info.txt').write_text(str(release_info), encoding='utf-8')

    return free_name, payload_root


def _make_temp_dir() -> str:
    import tempfile

    return tempfile.mkdtemp(prefix='sw-build-free-')


# ---------------------------------------------------------------------------
# Git plumbing
# ---------------------------------------------------------------------------


def _run_git(repo_root: str | Path, *args: str) -> subprocess.CompletedProcess:
    """Run git in ``repo_root`` without changing the process working directory."""
    try:
        result = subprocess.run(
            ['git', *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - git is a hard dependency
        raise FreePublishError('git executable not found') from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise FreePublishError(f"git {' '.join(args)} failed: {detail}")
    return result


def _run_git_bytes(
    repo_root: str | Path,
    *args: str,
    input_bytes: bytes | None = None,
) -> bytes:
    try:
        result = subprocess.run(
            ['git', *args],
            cwd=str(repo_root),
            input=input_bytes,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - git is a hard dependency
        raise FreePublishError('git executable not found') from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode('utf-8', 'replace').strip()
        raise FreePublishError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _ensure_clean(repo_root: str | Path) -> None:
    status = _run_git(repo_root, 'status', '--porcelain').stdout
    if status.strip():
        raise FreePublishError(
            'Free branch publication requires a clean working tree; '
            'commit or stash the changes first, or pass --skip-free.'
        )


def _ensure_origin(repo_root: str | Path) -> None:
    _run_git(repo_root, 'remote', 'get-url', 'origin')


def _remote_tip(repo_root: str | Path, branch: str) -> str | None:
    result = _run_git(repo_root, 'ls-remote', '--heads', 'origin', f'refs/heads/{branch}')
    output = result.stdout.strip()
    if not output:
        return None
    return output.splitlines()[0].split()[0]


def _fetch_branch(repo_root: str | Path, branch: str) -> None:
    _run_git(repo_root, 'fetch', '--no-tags', 'origin', f'refs/heads/{branch}')


def _hash_file(repo_root: str | Path, file_path: Path) -> str:
    output = _run_git_bytes(repo_root, 'hash-object', '-w', '--no-filters', '--', str(file_path))
    return output.decode().strip()


def _hash_symlink(repo_root: str | Path, file_path: Path) -> str:
    target = os.fsencode(os.readlink(file_path))
    output = _run_git_bytes(
        repo_root, 'hash-object', '-w', '--no-filters', '--stdin', input_bytes=target
    )
    return output.decode().strip()


def _write_tree(repo_root: str | Path, directory: Path) -> str:
    entries: list[tuple[str, str, str, str]] = []
    for child in sorted(directory.iterdir(), key=lambda item: item.name):
        name = child.name
        if name in ('', '.', '..') or '/' in name:
            raise FreePublishError(f'Unsupported payload file name: {name!r}')

        if child.is_symlink():
            entries.append(('120000', 'blob', _hash_symlink(repo_root, child), name))
        elif child.is_dir():
            entries.append(('040000', 'tree', _write_tree(repo_root, child), name))
        elif child.is_file():
            executable = child.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            mode = '100755' if executable else '100644'
            entries.append((mode, 'blob', _hash_file(repo_root, child), name))

    data = b''.join(
        f'{mode} {type_} {sha}\t'.encode() + name.encode('utf-8', 'surrogateescape') + b'\0'
        for mode, type_, sha, name in entries
    )
    output = _run_git_bytes(repo_root, 'mktree', '-z', input_bytes=data)
    return output.decode().strip()


def _write_payload_tree(repo_root: str | Path, payload_root: Path) -> str:
    if not payload_root.is_dir():
        raise FreePublishError(f'Free payload directory does not exist: {payload_root}')
    return _write_tree(repo_root, payload_root)


def _ls_tree(repo_root: str | Path, treeish: str) -> dict[str, tuple[str, str, str]]:
    output = _run_git_bytes(repo_root, 'ls-tree', '-r', '-z', treeish)
    entries: dict[str, tuple[str, str, str]] = {}
    for record in output.split(b'\0'):
        if not record:
            continue
        meta, name = record.split(b'\t', 1)
        mode, type_, sha = meta.split(b' ')
        entries[name.decode('utf-8', 'surrogateescape')] = (
            mode.decode(),
            type_.decode(),
            sha.decode(),
        )
    return entries


def _release_info_pairs(text: str) -> list[tuple[str, str]]:
    """Return the key/value rows of a release record, ignoring ``Created``.

    Formatting differences (border widths, box-drawing characters) are
    normalized away; only semantic rows are compared.
    """
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = _ROW_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key == 'Created':
            continue
        pairs.append((key, value))
    return pairs


def _compare_trees(
    repo_root: str | Path,
    previous_tree: str,
    payload_tree: str,
) -> tuple[bool, bool]:
    """Compare two trees, ignoring only ``release_info.txt``'s ``Created`` row.

    Returns ``(equivalent, timestamp_only)``.
    """
    if previous_tree == payload_tree:
        return True, False

    previous = _ls_tree(repo_root, previous_tree)
    current = _ls_tree(repo_root, payload_tree)
    if previous.keys() != current.keys():
        return False, False

    for path, previous_entry in previous.items():
        current_entry = current[path]
        if previous_entry[:2] != current_entry[:2]:
            return False, False
        if path == 'release_info.txt':
            previous_text = _run_git(
                repo_root, 'cat-file', '-p', f'{previous_tree}:{path}'
            ).stdout
            current_text = _run_git(repo_root, 'cat-file', '-p', f'{payload_tree}:{path}').stdout
            if _release_info_pairs(previous_text) != _release_info_pairs(current_text):
                return False, False
        elif previous_entry[2] != current_entry[2]:
            return False, False

    return True, True


def _commit_tree(
    repo_root: str | Path,
    payload_tree: str,
    previous_tip: str | None,
    version: str,
) -> str:
    args = ['commit-tree', payload_tree, '-m', f'Free release v{version}']
    if previous_tip is not None:
        args.extend(['-p', previous_tip])
    return _run_git(repo_root, *args).stdout.strip()


def _push(repo_root: str | Path, commit: str, branch: str) -> None:
    _run_git(repo_root, 'push', 'origin', f'{commit}:refs/heads/{branch}')


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------


def publish_free_branch(
    *,
    repo_root: str | Path,
    payload_root: str | Path,
    branch: str,
    version: str,
    console: Console | None = None,
) -> FreeSnapshot:
    """Publish ``payload_root`` as an append-only snapshot on ``origin/<branch>``."""
    repo_root = Path(repo_root)
    payload_root = Path(payload_root)
    output_console = console or _silent_console()

    _ensure_clean(repo_root)
    _ensure_origin(repo_root)

    previous_tip = _remote_tip(repo_root, branch)
    if previous_tip is not None:
        _fetch_branch(repo_root, branch)

    payload_tree = _write_payload_tree(repo_root, payload_root)

    if previous_tip is not None:
        previous_tree = _run_git(
            repo_root, 'rev-parse', f'{previous_tip}^{{tree}}'
        ).stdout.strip()
        equivalent, timestamp_only = _compare_trees(repo_root, previous_tree, payload_tree)
        if equivalent:
            output_console.print(
                f'[yellow]→ Free branch {branch} is unchanged at {previous_tip[:12]}[/]'
            )
            return FreeSnapshot(
                branch=branch,
                version=version,
                previous_tip=previous_tip,
                payload_tree=payload_tree,
                commit=None,
                committed=False,
                pushed=False,
                timestamp_only=timestamp_only,
            )

    commit = _commit_tree(repo_root, payload_tree, previous_tip, version)
    _push(repo_root, commit, branch)
    output_console.print(f'[green]✓ Published free branch {branch} at {commit[:12]}[/]')

    return FreeSnapshot(
        branch=branch,
        version=version,
        previous_tip=previous_tip,
        payload_tree=payload_tree,
        commit=commit,
        committed=True,
        pushed=True,
        timestamp_only=False,
    )
