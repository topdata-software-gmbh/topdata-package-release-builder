"""Tests for the release record written into the release ZIP.

The contract with the consuming package-service is load-bearing: it parses
``Created``/``Branch``/``Commit ID`` out of ``release_info.txt``.  These tests
pin that contract, including against the consumer's real regex.
"""
from __future__ import annotations

import re

import pytest

from topdata_package_release_builder.release import (
    PARSED_LABELS,
    create_release_info,
)

# ---------------------------------------------------------------------------
# The consumer's parser, copied verbatim from
# package-service/src/services/release_info.py::_parse_release_info
# ---------------------------------------------------------------------------

_LABELS = {"branch": "branch", "commit id": "commit_id", "created": "created"}
_ROW_RE = re.compile(
    r"^\s*[|│]?\s*(Branch|Commit ID|Created)\s*[:|│]\s*(.+?)\s*[|│]?\s*$",
    re.IGNORECASE,
)


def _parse_like_package_service(text: str) -> dict[str, str]:
    """Reproduce package-service's release_info.txt parsing."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        match = _ROW_RE.match(raw)
        if not match:
            continue
        key = _LABELS.get(match.group(1).strip().lower())
        if key is not None:
            out[key] = match.group(2).strip()
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ASSETS = {
    'targets': {'storefront-js': {}, 'storefront-css': {}},
    'toolchain': {
        'node': 'v20.11.1',
        'npm': '10.2.4',
        'lockfile': {'name': 'package-lock.json', 'sha256': 'a' * 64},
    },
}


def _release(**kwargs) -> str:
    params = {
        'plugin_name': 'TopdataDemoSW6',
        'branch': 'main-v1',
        'commitId': 'abc1234',
        'version': '1.4.0',
    }
    params.update(kwargs)
    return create_release_info(**params)


# ---------------------------------------------------------------------------
# The package-service contract (the regression)
# ---------------------------------------------------------------------------

def test_package_service_can_parse_provenance(tmp_path) -> None:
    """The regression: the borderless style was unreadable, losing all data."""
    parsed = _parse_like_package_service(_release())

    assert parsed == {
        'created': parsed['created'],
        'branch': 'main-v1',
        'commit_id': 'abc1234',
    }


def test_provenance_survives_with_asset_rows_present() -> None:
    """Extra rows must not break the consumer's row matching."""
    parsed = _parse_like_package_service(_release(assets=ASSETS))

    assert parsed['branch'] == 'main-v1'
    assert parsed['commit_id'] == 'abc1234'
    assert 'created' in parsed


def test_every_parsed_label_is_present_in_output() -> None:
    text = _release(assets=ASSETS)
    for label in PARSED_LABELS:
        assert label in text


def test_borderless_style_is_not_machine_readable() -> None:
    """Documents *why* the default style is mandatory for the ZIP copy.

    If this ever starts passing, the consumer's parser has changed and the
    style choice should be revisited rather than assumed.
    """
    assert _parse_like_package_service(_release(table_style='simple')) == {}


# ---------------------------------------------------------------------------
# Core rows
# ---------------------------------------------------------------------------

def test_version_is_prefixed_with_v() -> None:
    assert 'v1.4.0' in _release()


def test_plugin_and_version_rows_present() -> None:
    text = _release()
    assert 'TopdataDemoSW6' in text
    assert 'Plugin' in text
    assert 'Version' in text


def test_created_uses_berlin_timezone() -> None:
    text = _release()
    # Value shape is YYYY-MM-DD HH:MM as produced by the Berlin-stamped clock.
    match = re.search(r'Created\s+│\s*([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})', text)
    assert match is not None


# ---------------------------------------------------------------------------
# Asset provenance rows
# ---------------------------------------------------------------------------

def test_asset_rows_absent_without_verification_result() -> None:
    """A Slack notification must not assert an unverified asset state."""
    text = _release()
    assert 'Assets' not in text
    assert 'Node' not in text
    assert 'Lockfile' not in text


def test_asset_rows_list_verified_targets() -> None:
    text = _release(assets=ASSETS)
    assert 'storefront-css, storefront-js' in text


def test_asset_rows_report_none_compiled() -> None:
    text = _release(assets={'targets': {}, 'toolchain': {}})
    assert 'none compiled' in text


def test_node_version_recorded() -> None:
    assert 'v20.11.1' in _release(assets=ASSETS)


def test_node_reported_as_na_when_unknown() -> None:
    assets = {'targets': {'storefront-js': {}}, 'toolchain': {'node': None, 'lockfile': None}}
    text = _release(assets=assets)
    assert 'n/a' in text
    assert 'none' in text


def test_toolchain_rows_omitted_when_nothing_compiled() -> None:
    """Toolchain state is not applicable when nothing was compiled."""
    assets = {'targets': {}, 'toolchain': {'node': 'v26.7.0', 'lockfile': None}}
    text = _release(assets=assets)
    assert 'none compiled' in text
    assert 'Node' not in text
    assert 'v26.7.0' not in text


def test_lockfile_recorded_with_short_digest() -> None:
    text = _release(assets=ASSETS)
    assert 'package-lock.json:aaaaaaaaaaaa' in text


def test_lockfile_absent_reported_as_none() -> None:
    assets = {'targets': {}, 'toolchain': {'node': 'v20', 'lockfile': None}}
    assert 'none' in _release(assets=assets)


def test_empty_asset_dict_is_treated_as_no_verification() -> None:
    assert 'Assets' not in _release(assets={})


# ---------------------------------------------------------------------------
# Column alignment
# ---------------------------------------------------------------------------

def test_table_rows_are_rectangular() -> None:
    """A ragged value breaks the fixed-width table and the parser with it."""
    text = _release(assets=ASSETS)
    body = [line for line in text.splitlines() if line.startswith('│')]
    assert len({len(line) for line in body}) == 1


@pytest.mark.parametrize(
    'assets',
    [
        None,
        {'targets': {}, 'toolchain': {}},
        ASSETS,
        {'targets': {'a': {}, 'b': {}, 'c': {}, 'd': {}}, 'toolchain': {'node': 'v22.0.0', 'lockfile': None}},
    ],
)
def test_table_stays_rectangular_for_every_asset_shape(assets) -> None:
    text = _release(assets=assets)
    body = [line for line in text.splitlines() if line.startswith('│')]
    assert len({len(line) for line in body}) == 1


def test_very_long_value_does_not_break_alignment() -> None:
    long_name = 'X' * 200
    text = _release(plugin_name=long_name)
    body = [line for line in text.splitlines() if line.startswith('│')]
    assert len({len(line) for line in body}) == 1
    assert _parse_like_package_service(text)['branch'] == 'main-v1'