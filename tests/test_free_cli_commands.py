"""CLI tests for the ``sw-build free`` command group and legacy build routing."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

import topdata_package_release_builder.cli as cli
from topdata_package_release_builder.free_manifest import load_free_manifest


def _invoke(*args: str):
    return CliRunner().invoke(cli.cli, list(args))


def _read(plugin_root: Path) -> str:
    return (plugin_root / '.topdata' / 'build.yaml').read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# free enable
# ---------------------------------------------------------------------------


def test_free_enable_creates_manifest(tmp_path: Path) -> None:
    result = _invoke('free', 'enable', '--source-dir', str(tmp_path))

    assert result.exit_code == 0, result.output
    assert (tmp_path / '.topdata' / 'build.yaml').is_file()
    manifest = load_free_manifest(tmp_path)
    assert manifest.enabled is True
    assert manifest.branch == 'main-free'
    assert manifest.zip is False


def test_free_enable_writes_branch_and_zip(tmp_path: Path) -> None:
    result = _invoke(
        'free', 'enable', '--source-dir', str(tmp_path), '--branch', 'free-latest', '--zip'
    )

    assert result.exit_code == 0, result.output
    manifest = load_free_manifest(tmp_path)
    assert manifest.branch == 'free-latest'
    assert manifest.zip is True


def test_free_enable_rejects_invalid_branch_without_writing(tmp_path: Path) -> None:
    result = _invoke('free', 'enable', '--source-dir', str(tmp_path), '--branch', 'bad~branch')

    assert result.exit_code != 0
    assert 'free.branch' in result.output
    assert not (tmp_path / '.topdata').exists()


def test_free_enable_preserves_existing_manifest(tmp_path: Path) -> None:
    path = tmp_path / '.topdata' / 'build.yaml'
    path.parent.mkdir(parents=True)
    path.write_text('other: value\nfree:\n  branch: keep-me\n', encoding='utf-8')

    result = _invoke('free', 'enable', '--source-dir', str(tmp_path), '--zip')

    assert result.exit_code == 0, result.output
    content = _read(tmp_path)
    assert 'other: value' in content
    assert 'keep-me' in content
    assert 'zip: true' in content


# ---------------------------------------------------------------------------
# free disable
# ---------------------------------------------------------------------------


def test_free_disable_removes_manifest(tmp_path: Path) -> None:
    assert _invoke('free', 'enable', '--source-dir', str(tmp_path)).exit_code == 0

    result = _invoke('free', 'disable', '--source-dir', str(tmp_path))

    assert result.exit_code == 0, result.output
    assert not (tmp_path / '.topdata' / 'build.yaml').exists()
    assert load_free_manifest(tmp_path).enabled is False


def test_free_disable_twice_succeeds(tmp_path: Path) -> None:
    assert _invoke('free', 'enable', '--source-dir', str(tmp_path)).exit_code == 0
    assert _invoke('free', 'disable', '--source-dir', str(tmp_path)).exit_code == 0

    result = _invoke('free', 'disable', '--source-dir', str(tmp_path))

    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# free status
# ---------------------------------------------------------------------------


def test_free_status_reports_enabled_and_disabled(tmp_path: Path) -> None:
    disabled = _invoke('free', 'status', '--source-dir', str(tmp_path))
    assert disabled.exit_code == 0, disabled.output
    assert 'disabled' in disabled.output

    assert _invoke('free', 'enable', '--source-dir', str(tmp_path), '--branch', 'free-latest').exit_code == 0

    enabled = _invoke('free', 'status', '--source-dir', str(tmp_path))
    assert enabled.exit_code == 0, enabled.output
    assert 'enabled' in enabled.output
    assert 'free-latest' in enabled.output
    assert 'main-free' not in enabled.output
    assert 'disabled' in enabled.output.split('ZIP:', 1)[1]


# ---------------------------------------------------------------------------
# invalid manifests
# ---------------------------------------------------------------------------


def test_commands_reject_invalid_manifest_without_writing(tmp_path: Path) -> None:
    path = tmp_path / '.topdata' / 'build.yaml'
    path.parent.mkdir(parents=True)
    path.write_text('free: [unclosed\n', encoding='utf-8')
    original = path.read_bytes()

    results = [
        _invoke('free', 'enable', '--source-dir', str(tmp_path)),
        _invoke('free', 'disable', '--source-dir', str(tmp_path)),
        _invoke('free', 'status', '--source-dir', str(tmp_path)),
    ]

    for result in results:
        assert result.exit_code != 0
        assert 'Invalid YAML' in result.output
    assert path.read_bytes() == original


# ---------------------------------------------------------------------------
# legacy build routing
# ---------------------------------------------------------------------------


@pytest.fixture
def recorded_build(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    def _record(**kwargs) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli.build_plugin, 'callback', _record)
    return calls


def test_legacy_options_route_to_build(recorded_build, tmp_path: Path) -> None:
    result = _invoke(
        '--source-dir', str(tmp_path), '--output-dir', str(tmp_path / 'out'), '--version-increment', 'none'
    )

    assert result.exit_code == 0, result.output
    assert len(recorded_build) == 1
    assert recorded_build[0]['source_dir'] == str(tmp_path)
    assert recorded_build[0]['version_increment'] == 'none'


def test_no_arguments_routes_to_build(recorded_build) -> None:
    result = _invoke()

    assert result.exit_code == 0, result.output
    assert len(recorded_build) == 1


def test_explicit_build_command_routes_to_build(recorded_build, tmp_path: Path) -> None:
    result = _invoke('build', '--source-dir', str(tmp_path), '--version-increment', 'none')

    assert result.exit_code == 0, result.output
    assert len(recorded_build) == 1


def test_free_status_does_not_run_build(recorded_build, tmp_path: Path) -> None:
    result = _invoke('free', 'status', '--source-dir', str(tmp_path))

    assert result.exit_code == 0, result.output
    assert recorded_build == []


def test_help_lists_build_and_free() -> None:
    result = _invoke('--help')

    assert result.exit_code == 0, result.output
    assert 'build' in result.output
    assert 'free' in result.output
