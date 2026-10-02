"""Compiled-asset verification for the release build.

Why this module exists
----------------------
The previous check compared *modification times* of asset sources against
compiled output.  That is unreliable in the exact situation it was meant to
protect: ``git clone``, ``git pull`` and ``rsync`` all rewrite mtimes, so a
freshly cloned checkout -- the one most likely to ship uncompiled assets --
produced an arbitrary answer rather than a verdict.  Worse, the comparison
was skipped whenever compiled output was *absent*, so a plugin with asset
sources and no build at all was reported as "up-to-date".

Freshness is therefore decided by SHA-256 *content* hashes, and absence of
compiled output is a first-class outcome rather than a skipped check.

The manifest
------------
``verify_assets`` records the source and output digests in
``.git/sw-build/<plugin>/.sw-build-assets.json``.  That file is deliberately
*local* state: it lives inside the git directory, so it never reaches the
release ZIP, is never reported by ``git status``, and cannot be shared with
another developer's checkout.  A first build in a fresh checkout has nothing
to compare against and records a baseline; every later build in that same
checkout is checked against it.

Only a *passing* verification updates the baseline.  That is the whole point:
if a stale target were recorded anyway, the next run would compare against
the edited source digest and pass, permanently blessing compiled output that
was never rebuilt.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_NAME = '.sw-build-assets.json'
MANIFEST_SCHEMA = 1
PUBLIC_SUBDIR = 'src/Resources/public'

#: Lockfiles we recognise, in order of preference.
LOCKFILES = ('package-lock.json', 'pnpm-lock.yaml', 'yarn.lock')


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssetTarget:
    """One compilation unit: a source tree and the output it should produce."""

    name: str
    label: str
    src_dir: str
    dist_dir: str
    src_ext: tuple[str, ...]
    dist_ext: tuple[str, ...]


TARGETS: tuple[AssetTarget, ...] = (
    AssetTarget(
        name='administration-js',
        label='Administration JS',
        src_dir='src/Resources/app/administration/src',
        dist_dir='src/Resources/public/administration/js',
        src_ext=('.ts', '.js'),
        dist_ext=('.js',),
    ),
    AssetTarget(
        name='storefront-js',
        label='Storefront JS',
        src_dir='src/Resources/app/storefront/src',
        dist_dir='src/Resources/public/storefront/js',
        src_ext=('.ts', '.js'),
        dist_ext=('.js',),
    ),
    AssetTarget(
        name='storefront-css',
        label='Storefront CSS',
        src_dir='src/Resources/app/storefront/src',
        dist_dir='src/Resources/public/storefront/css',
        src_ext=('.scss', '.css'),
        dist_ext=('.css',),
    ),
)


# ---------------------------------------------------------------------------
# Content digests
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TreeDigest:
    """A content-addressed summary of a directory tree."""

    sha256: str
    files: int
    paths: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Serialise for the manifest."""
        return {'sha256': self.sha256, 'files': self.files}


def digest_tree(
    root: str | os.PathLike[str],
    extensions: Sequence[str] = (),
    *,
    exclude: Iterable[str] = (),
) -> TreeDigest:
    """Hash every matching file below *root* by path and content.

    The digest depends only on relative paths and file bytes, so it is
    identical across machines, clones and checkouts -- which is precisely
    what an mtime comparison is not.

    Args:
        root: Directory to walk. A missing directory digests as empty.
        extensions: Only files ending with one of these are included. An
            empty sequence includes every file.
        exclude: File names to skip regardless of extension.

    Returns:
        The tree's :class:`TreeDigest`.
    """
    excluded = set(exclude)
    entries: list[tuple[str, str]] = []
    root_str = os.fspath(root)

    if os.path.isdir(root_str):
        for dirpath, dirnames, filenames in os.walk(root_str):
            dirnames[:] = sorted(d for d in dirnames if d != 'node_modules')
            for name in filenames:
                if name in excluded:
                    continue
                if extensions and not any(name.endswith(ext) for ext in extensions):
                    continue
                full = os.path.join(dirpath, name)
                try:
                    with open(full, 'rb') as handle:
                        content = handle.read()
                except OSError:
                    # A file vanishing mid-walk is not a reason to fail a build.
                    continue
                rel = os.path.relpath(full, root_str).replace(os.sep, '/')
                entries.append((rel, hashlib.sha256(content).hexdigest()))

    entries.sort()
    hasher = hashlib.sha256()
    for rel, content_sha in entries:
        hasher.update(rel.encode('utf-8'))
        hasher.update(b'\0')
        hasher.update(content_sha.encode('ascii'))
        hasher.update(b'\0')
    return TreeDigest(
        sha256=hasher.hexdigest(),
        files=len(entries),
        paths=tuple(rel for rel, _ in entries),
    )


def compiled_assets_present(plugin_root: str | os.PathLike[str]) -> bool:
    """Return True when *plugin_root* ships any compiled asset at all.

    This is the signal that decides whether a missing target is an error
    (the plugin compiles things, so this one is simply forgotten) or a
    warning (the plugin never compiles anything, so demanding output would
    be wrong).
    """
    public_root = Path(plugin_root) / PUBLIC_SUBDIR
    return digest_tree(public_root, ('.js', '.css', '.map'), exclude=(MANIFEST_NAME,)).files > 0


# ---------------------------------------------------------------------------
# Toolchain provenance
# ---------------------------------------------------------------------------

def _tool_version(executable: str) -> str | None:
    """Return ``<exe> --version`` output, or None if it cannot be run."""
    path = shutil.which(executable)
    if path is None:
        return None
    try:
        completed = subprocess.run(
            [path, '--version'],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = (completed.stdout or completed.stderr).strip()
    return value or None


def toolchain_provenance(plugin_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Collect what can be said about the toolchain that built the assets.

    Best-effort by design: absent values are reported as ``None`` rather than
    guessed, so the release record distinguishes "not installed here" from
    "version 0".
    """
    lock: dict[str, Any] | None = None
    for name in LOCKFILES:
        candidate = Path(plugin_root) / name
        if candidate.is_file():
            try:
                digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            except OSError:
                digest = ''
            lock = {'name': name, 'sha256': digest}
            break

    return {
        'node': _tool_version('node'),
        'npm': _tool_version('npm'),
        'lockfile': lock,
    }


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def _git_state_dir(plugin_root: str | os.PathLike[str]) -> Path:
    """Return a per-checkout directory for tool state, inside ``.git``.

    The manifest must not live in the working tree: ``src/Resources/public``
    is copied into the release ZIP, and any new path in the working tree
    shows up in ``git status`` -- which makes ``sw-build`` offer to stage and
    commit its own state. Both are avoided by keeping it under the git
    directory, which git never reports and the ZIP already excludes.

    The plugin name is part of the directory so that plugins sharing one
    repository (a monorepo) cannot overwrite each other's manifest.
    """
    root = Path(plugin_root)
    git_dir: Path | None = None
    try:
        completed = subprocess.run(
            ['git', '-C', str(root), 'rev-parse', '--absolute-git-dir'],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            git_dir = Path(completed.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        git_dir = None

    if git_dir is None:
        candidate = root / '.git'
        git_dir = candidate if candidate.is_dir() else root / '.sw-build'

    return git_dir / 'sw-build' / (root.name or 'plugin')


def manifest_path(plugin_root: str | os.PathLike[str]) -> Path:
    """Return the manifest location for *plugin_root*."""
    return _git_state_dir(plugin_root) / MANIFEST_NAME


def read_manifest(plugin_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Load the manifest, returning ``{}`` for missing, stale or broken ones.

    A manifest we cannot trust is treated as absent rather than fatal: the
    worst case is a missed staleness report, not a failed release.
    """
    path = manifest_path(plugin_root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get('schema') != MANIFEST_SCHEMA:
        return {}
    if not isinstance(data.get('targets'), dict):
        return {}
    return data


def write_manifest(plugin_root: str | os.PathLike[str], data: dict[str, Any]) -> None:
    """Persist *data* as the manifest for *plugin_root*."""
    path = manifest_path(plugin_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

@dataclass
class AssetVerification:
    """Outcome of :func:`verify_assets`."""

    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    targets: dict[str, Any] = field(default_factory=dict)
    manifest_written: bool = False
    toolchain: dict[str, Any] = field(default_factory=dict)

    @property
    def compiled_targets(self) -> list[str]:
        """Labels of targets that were verified against compiled output."""
        return list(self.targets)


def _describe_digest(digest: TreeDigest) -> str:
    """Human-readable one-liner for a digest."""
    return f'{digest.files} file(s), sha256 {digest.sha256[:12]}'


def verify_assets(
    plugin_root: str,
    *,
    strict: bool = False,
    verbose: bool = False,
    debug: bool = False,
    console: Any = None,
) -> AssetVerification:
    """Verify compiled assets against their sources using content hashes.

    Args:
        plugin_root: Root of the plugin checkout.
        strict: Treat any target with sources but no compiled output as an
            error. By default that is only an error when some *other* target
            of the same plugin did compile, because most Topdata plugins
            ship hand-written Twig and CSS and have no build at all.
        verbose: Print per-target detail.
        debug: Print the digests behind every decision.
        console: Optional rich console for output.

    Returns:
        An :class:`AssetVerification`; ``ok`` is False only when a target is
        genuinely stale or (under *strict*) uncompiled.
    """
    result = AssetVerification()
    previous_targets = read_manifest(plugin_root).get('targets', {})

    def emit(message: str, style: str) -> None:
        if console is not None:
            console.print(message, style=style)

    # ---- Digest every target once, before drawing any conclusion ---------
    digests: list[tuple[AssetTarget, TreeDigest, TreeDigest]] = []
    for target in TARGETS:
        src = digest_tree(Path(plugin_root) / target.src_dir, target.src_ext)
        if src.files == 0:
            if verbose:
                result.notes.append(f'{target.label}: no sources, nothing to build')
            continue
        dist = digest_tree(
            Path(plugin_root) / target.dist_dir,
            target.dist_ext,
            exclude=(MANIFEST_NAME,),
        )
        digests.append((target, src, dist))

    # A plugin compiles if any target it *has sources for* also produced
    # output. Judging the whole plugin instead would treat a hand-written
    # `public/storefront/css/base.css` as proof of a build and block a
    # plugin that legitimately compiles nothing.
    compiles = any(dist.files > 0 for _t, _s, dist in digests)

    for target, src, dist in digests:
        # ---- Compiled output is missing entirely -------------------------
        if dist.files == 0:
            if strict or compiles:
                result.errors.append(
                    f'{target.label}: {src.files} source file(s) present but no compiled '
                    f'output in {target.dist_dir}/ - run the asset build'
                )
            else:
                result.warnings.append(
                    f'{target.label}: {src.files} source file(s) in {target.src_dir}/ but this '
                    f'plugin ships no compiled assets from a build, so they are shipped '
                    f'uncompiled'
                )
            continue

        # ---- Compiled output exists: compare against the baseline ---------
        previous = previous_targets.get(target.name)
        stale = False
        if not isinstance(previous, dict):
            result.notes.append(
                f'{target.label}: recording first asset baseline for this checkout'
            )
        else:
            prev_src = (previous.get('sources') or {}).get('sha256')
            prev_out = (previous.get('output') or {}).get('sha256')
            if prev_src and prev_src != src.sha256:
                stale = True
                result.errors.append(
                    f'{target.label}: asset sources changed since the last verified build '
                    f'- recompile before releasing'
                )
            elif prev_out and prev_out != dist.sha256:
                result.warnings.append(
                    f'{target.label}: compiled output changed without a source change since '
                    f'the last verified build'
                )

        # A stale target must not advance the baseline: recording the edited
        # source digest here would make the *next* build compare against it
        # and pass, permanently blessing output that was never recompiled.
        if not stale:
            result.targets[target.name] = {
                'sources': src.as_dict(),
                'output': dist.as_dict(),
            }

        if debug:
            emit(
                f'[dim]  {target.label}: sources {_describe_digest(src)} | '
                f'output {_describe_digest(dist)}[/dim]',
                style=None,
            )

    result.ok = not result.errors
    result.toolchain = toolchain_provenance(plugin_root)

    # Persist the baseline only for a verification that actually passed. A
    # failed run must leave the previous baseline untouched, otherwise one
    # ignored error would bless stale output on the next attempt.
    if result.ok and result.targets:
        write_manifest(
            plugin_root,
            {
                'schema': MANIFEST_SCHEMA,
                'tool': 'sw-build',
                'toolchain': result.toolchain,
                'targets': result.targets,
            },
        )
        result.manifest_written = True

    if verbose or debug:
        for note in result.notes:
            emit(f'[dim]{note}[/dim]', style=None)

    return result
