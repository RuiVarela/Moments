"""Frontend JS checks via Node (skipped if Node absent)."""
import json
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

_JS_DIR = Path(__file__).parent.parent / "src" / "moments" / "static" / "js"
_NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(_NODE is None, reason="node not installed")


def _js_files() -> list[Path]:
    return sorted(_JS_DIR.rglob("*.js"))


@pytest.mark.parametrize("js_file", _js_files(), ids=lambda p: p.name)
def test_js_syntax(js_file: Path) -> None:
    """Each module parses (catches duplicate declarations, typos)."""
    assert _NODE is not None
    result = subprocess.run(
        [_NODE, "--check", str(js_file)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def _parse_route(hash_value: str) -> dict[str, object]:
    """Run Route.parse() in Node with stubbed browser globals."""
    assert _NODE is not None
    router_url = (_JS_DIR / "router.js").as_uri()
    script = f"""
globalThis.window = {{ addEventListener() {{}} }};
globalThis.location = {{ hash: {json.dumps(hash_value)} }};
const {{ Route }} = await import({json.dumps(router_url)});
const r = Route.parse();
console.log(JSON.stringify({{ path: r.path, albumId: r.albumId, mediaHash: r.mediaHash, str: r.toString() }}));
"""
    result = subprocess.run(
        [_NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    parsed: dict[str, object] = json.loads(result.stdout)
    return parsed


@pytest.mark.parametrize(
    ("hash_value", "path", "album", "media"),
    [
        ("", "", None, None),
        ("#/", "", None, None),
        ("#/a/vacation", "a", "vacation", None),
        ("#/a/my%20trip", "a", "my trip", None),
        ("#/a/vacation/m/abc123", "m", "vacation", "abc123"),
        ("#/unknown", "", None, None),
    ],
)
def test_route_parse(
    hash_value: str, path: str, album: str | None, media: str | None
) -> None:
    """Route.parse() maps hash URLs to views."""
    r = _parse_route(hash_value)
    assert r["path"] == path
    assert r["albumId"] == album
    assert r["mediaHash"] == media


def test_route_roundtrip() -> None:
    """toString() output parses back to same route."""
    r = _parse_route("#/a/my%20trip/m/abc123")
    assert r["str"] == "#/a/my%20trip/m/abc123"


def _group_by_month(items: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Run dates.groupByMonth() in Node (UTC, en-US) → [{label, count}]."""
    assert _NODE is not None
    dates_url = (_JS_DIR / "dates.js").as_uri()
    script = f"""
const {{ groupByMonth }} = await import({json.dumps(dates_url)});
const groups = groupByMonth({json.dumps(items)}, "en-US");
console.log(JSON.stringify(groups.map(g => ({{ label: g.label, count: g.items.length }}))));
"""
    result = subprocess.run(
        [_NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        env={"TZ": "UTC"},
    )
    assert result.returncode == 0, result.stderr
    groups: list[dict[str, object]] = json.loads(result.stdout)
    return groups


# UTC timestamps.
_MAR_03_2006 = 1141344000
_MAR_20_2006 = 1142812800
_APR_01_2006 = 1143849600


def test_group_by_month_ascending() -> None:
    """Consecutive same-month items share a header; undated grouped last."""
    items: list[dict[str, int | None]] = [
        {"date": _MAR_03_2006},
        {"date": _MAR_20_2006},
        {"date": _APR_01_2006},
        {"date": None},
    ]

    assert _group_by_month(items) == [
        {"label": "March 2006", "count": 2},
        {"label": "April 2006", "count": 1},
        {"label": "Undated", "count": 1},
    ]


def test_group_by_month_descending() -> None:
    """Order follows input (server already sorted)."""
    items = [{"date": _APR_01_2006}, {"date": _MAR_20_2006}, {"date": _MAR_03_2006}]

    assert _group_by_month(items) == [
        {"label": "April 2006", "count": 1},
        {"label": "March 2006", "count": 2},
    ]


def test_group_by_month_same_month_other_year() -> None:
    """March 2006 ≠ March 2007."""
    mar_2007 = _MAR_03_2006 + 365 * 24 * 3600

    assert [g["label"] for g in _group_by_month([{"date": _MAR_03_2006}, {"date": mar_2007}])] == [
        "March 2006",
        "March 2007",
    ]
