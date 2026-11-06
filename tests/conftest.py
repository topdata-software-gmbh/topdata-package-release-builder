"""Shared fixtures for the main-free branch tests.

Publication tests run against real temporary git repositories: a bare
``origin`` plus a working plugin clone. That keeps the append-only, no-force
and untouched-checkout guarantees observable instead of mocked.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_GIT_ENV = {
    'GIT_AUTHOR_NAME': 'Test',
    'GIT_AUTHOR_EMAIL': 'test@example.com',
    'GIT_COMMITTER_NAME': 'Test',
    'GIT_COMMITTER_EMAIL': 'test@example.com',
}


def run_git(*args: str, cwd: str | Path) -> str:
    """Run git in ``cwd`` and return stdout, raising on failure."""
    result = subprocess.run(
        ['git', *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env={**os.environ, **_GIT_ENV},
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed in {cwd}:\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def write_plugin(
    root: str | Path,
    name: str = 'TopdataDemoSW6',
    version: str = '1.4.0',
    *,
    use_foundation: bool = False,
) -> Path:
    """Write a minimal, committed-ready Shopware plugin into ``root``."""
    root = Path(root)
    (root / 'src').mkdir(parents=True, exist_ok=True)
    (root / 'src' / 'Resources' / 'app' / 'storefront').mkdir(parents=True, exist_ok=True)

    composer = {
        'name': 'topdata/demo-sw6',
        'version': version,
        'description': 'Demo plugin',
        'extra': {
            'shopware-plugin-class': f'Topdata\\{name}\\{name}',
            'label': {'de-DE': 'Demo', 'en-GB': 'Demo'},
        },
        'autoload': {'psr-4': {f'Topdata\\{name}\\': 'src/'}},
    }
    if use_foundation:
        composer['require'] = {'topdata/topdata-foundation-sw6': '*'}

    (root / 'composer.json').write_text(json.dumps(composer, indent=4), encoding='utf-8')

    use_line = 'use Topdata\\TopdataFoundationSW6\\Service\\Helper;\n' if use_foundation else ''
    (root / 'src' / f'{name}.php').write_text(
        '<?php\n'
        f'namespace Topdata\\{name};\n\n'
        f'{use_line}\n'
        f'class {name}\n{{\n'
        '    public function run(): void\n'
        '    {\n'
        '    }\n'
        '}\n',
        encoding='utf-8',
    )
    (root / 'README.md').write_text('# Demo\n', encoding='utf-8')
    return root


def write_foundation(root: str | Path) -> Path:
    """Write a minimal foundation plugin with a small dependency chain."""
    root = Path(root)
    (root / 'src' / 'Service').mkdir(parents=True, exist_ok=True)
    (root / 'src' / 'Util').mkdir(parents=True, exist_ok=True)

    (root / 'src' / 'Service' / 'Helper.php').write_text(
        '<?php\n'
        'namespace Topdata\\TopdataFoundationSW6\\Service;\n\n'
        'use Topdata\\TopdataFoundationSW6\\Util\\StringUtil;\n\n'
        'class Helper\n{\n'
        '    public function value(): string\n'
        '    {\n'
        '        return StringUtil::class;\n'
        '    }\n'
        '}\n',
        encoding='utf-8',
    )
    (root / 'src' / 'Util' / 'StringUtil.php').write_text(
        '<?php\n'
        'namespace Topdata\\TopdataFoundationSW6\\Util;\n\n'
        'class StringUtil\n{\n'
        '    public static function slug(string $value): string\n'
        '    {\n'
        '        return strtolower($value);\n'
        '    }\n'
        '}\n',
        encoding='utf-8',
    )
    (root / 'src' / 'Resources' / 'config').mkdir(parents=True, exist_ok=True)
    (root / 'src' / 'Resources' / 'config' / 'services.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<container xmlns="http://symfony.com/schema/dic/services">\n'
        '    <services>\n'
        '        <service id="Topdata\\TopdataFoundationSW6\\Service\\Helper"/>\n'
        '    </services>\n'
        '</container>\n',
        encoding='utf-8',
    )
    return root


@pytest.fixture
def git():
    """Expose the git helper to tests."""
    return run_git


@pytest.fixture
def make_foundation(tmp_path):
    """Factory that writes a foundation plugin and returns its path."""

    def _make(parent: str | Path | None = None) -> Path:
        root = Path(parent or tmp_path) / 'topdata-foundation-sw6'
        return write_foundation(root)

    return _make


@pytest.fixture
def plugin_repo(tmp_path):
    """A working plugin clone pushed to a bare ``origin``."""
    origin = tmp_path / 'origin.git'
    origin.mkdir()
    run_git('init', '--bare', '-b', 'main', cwd=origin)

    root = tmp_path / 'TopdataDemoSW6'
    root.mkdir()
    run_git('init', '-b', 'main', cwd=root)
    run_git('config', 'user.name', 'Test', cwd=root)
    run_git('config', 'user.email', 'test@example.com', cwd=root)
    write_plugin(root)
    run_git('add', '-A', cwd=root)
    run_git('commit', '-m', 'initial', cwd=root)
    run_git('remote', 'add', 'origin', str(origin), cwd=root)
    run_git('push', '-u', 'origin', 'main', cwd=root)

    return {
        'root': root,
        'origin': origin,
        'name': 'TopdataDemoSW6',
        'version': '1.4.0',
    }


@pytest.fixture
def foundation_plugin_repo(tmp_path):
    """A plugin clone that requires the foundation, plus the foundation checkout."""
    origin = tmp_path / 'origin.git'
    origin.mkdir()
    run_git('init', '--bare', '-b', 'main', cwd=origin)

    root = tmp_path / 'TopdataDemoSW6'
    root.mkdir()
    run_git('init', '-b', 'main', cwd=root)
    run_git('config', 'user.name', 'Test', cwd=root)
    run_git('config', 'user.email', 'test@example.com', cwd=root)
    write_plugin(root, use_foundation=True)
    run_git('add', '-A', cwd=root)
    run_git('commit', '-m', 'initial', cwd=root)
    run_git('remote', 'add', 'origin', str(origin), cwd=root)
    run_git('push', '-u', 'origin', 'main', cwd=root)

    foundation = write_foundation(tmp_path / 'topdata-foundation-sw6')

    return {
        'root': root,
        'origin': origin,
        'foundation': foundation,
        'name': 'TopdataDemoSW6',
        'version': '1.4.0',
    }
