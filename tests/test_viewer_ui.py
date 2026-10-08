"""Viewer behavior in real Chrome against a live server (skipped if Playwright/Chrome absent)."""
import re
import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import uvicorn

from moments.app import create_app
from moments.config import Config

playwright_api = pytest.importorskip("playwright.sync_api")

_HOST = "127.0.0.1"
_ALBUM = "vacation"
_POLL_TRIES = 250
_POLL_SEC = 0.02
_TIMEOUT_MS = 5000

# Wider than test images' 4:3, so fill zooms.
_VIEWPORT = {"width": 1200, "height": 600}
_CENTER = (600, 300)
_SETTLE_MS = 500  # > double-tap window and zoom animation.


def _free_port() -> int:
    with socket.socket() as s:
        s.bind((_HOST, 0))
        port: int = s.getsockname()[1]
        return port


@pytest.fixture
def base_url(config: Config, album_with_images: Path) -> Generator[str, None, None]:
    """Serve app in a background thread."""
    server = uvicorn.Server(uvicorn.Config(create_app(config), host=_HOST, port=_free_port(), log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    while not server.started:
        time.sleep(_POLL_SEC)

    yield f"http://{_HOST}:{server.config.port}"

    server.should_exit = True
    thread.join()


def _extract(page: "playwright_api.Page", base_url: str) -> str:
    """Run extraction, return first media hash."""
    api = f"{base_url}/api/albums/{_ALBUM}"
    page.request.post(f"{api}/extract")

    for _ in range(_POLL_TRIES):
        if page.request.get(f"{api}/extract/status").json()["status"] != "running":
            break
        time.sleep(_POLL_SEC)

    first: str = page.request.get(api).json()["items"][0]["hash"]
    return first


@pytest.fixture
def viewer(base_url: str) -> Generator["playwright_api.Page", None, None]:
    """Page showing the viewer on the album's first item."""
    with playwright_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except playwright_api.Error:
            pytest.skip("chrome not installed")

        page = browser.new_page(viewport=_VIEWPORT)
        first = _extract(page, base_url)
        page.goto(f"{base_url}/#/a/{_ALBUM}/m/{first}")
        page.wait_for_function("document.querySelector('.viewer-media')?.complete", timeout=_TIMEOUT_MS)

        yield page
        browser.close()


def _scale(page: "playwright_api.Page") -> float:
    """Media zoom scale from its computed transform matrix."""
    matrix: str = page.eval_on_selector(".viewer-media", "e => getComputedStyle(e).transform")
    match = re.match(r"matrix\(([^,]+)", matrix)
    return float(match.group(1)) if match else 1.0


def _fill_scale(page: "playwright_api.Page") -> float:
    """Scale at which media covers the stage."""
    scale: float = page.evaluate(
        """() => {
            const m = document.querySelector('.viewer-media');
            const s = document.querySelector('.viewer-stage').getBoundingClientRect();
            const k = Math.min(m.offsetWidth / m.naturalWidth, m.offsetHeight / m.naturalHeight);
            return Math.max(s.width / (m.naturalWidth * k), s.height / (m.naturalHeight * k));
        }"""
    )
    return scale


def _position(page: "playwright_api.Page") -> str:
    """Counter's "index /" part, e.g. "1 /"."""
    counter: str = page.text_content(".viewer-counter") or ""
    return counter.split("/")[0].strip()


def _drag(page: "playwright_api.Page", dx: int) -> None:
    x, y = _CENTER
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx, y, steps=5)
    page.mouse.up()


def test_arrows_leave_buttons_unfocused(viewer: "playwright_api.Page") -> None:
    """← → navigate without putting focus on top bar buttons."""
    viewer.keyboard.press("ArrowRight")
    viewer.keyboard.press("ArrowLeft")

    active = viewer.evaluate("() => document.activeElement.className")
    assert "viewer-btn" not in active


def test_clicked_button_stays_unfocused(viewer: "playwright_api.Page") -> None:
    """Mouse click on a bar button doesn't focus it (arrows would show its focus ring)."""
    viewer.click(".viewer-fullscreen")
    viewer.keyboard.press("ArrowRight")

    active = viewer.evaluate("() => document.activeElement.className")
    assert "viewer-btn" not in active


def test_first_display_fits(viewer: "playwright_api.Page") -> None:
    """Small image (400x300 cover) scales up to fit the stage on one axis."""
    fit: float = viewer.evaluate(
        """() => {
            const m = document.querySelector('.viewer-media');
            const r = m.getBoundingClientRect();
            const s = document.querySelector('.viewer-stage').getBoundingClientRect();
            const k = Math.min(r.width / m.naturalWidth, r.height / m.naturalHeight);
            return Math.max(m.naturalWidth * k / s.width, m.naturalHeight * k / s.height);
        }"""
    )
    assert fit == pytest.approx(1)


def test_wheel_zooms(viewer: "playwright_api.Page") -> None:
    """Wheel up zooms in; wheel down returns to fit, not below."""
    viewer.mouse.move(*_CENTER)
    viewer.mouse.wheel(0, -300)
    viewer.wait_for_timeout(100)
    assert _scale(viewer) > 1

    viewer.mouse.wheel(0, 3000)
    viewer.wait_for_timeout(100)
    assert _scale(viewer) == 1


def test_double_tap_toggles_fill(viewer: "playwright_api.Page") -> None:
    """Double tap: fit → fill → fit."""
    fill = _fill_scale(viewer)
    assert fill > 1

    viewer.mouse.dblclick(*_CENTER)
    viewer.wait_for_timeout(_SETTLE_MS)
    assert _scale(viewer) == pytest.approx(fill)

    viewer.mouse.dblclick(*_CENTER)
    viewer.wait_for_timeout(_SETTLE_MS)
    assert _scale(viewer) == 1


def test_double_tap_keeps_top_bar(viewer: "playwright_api.Page") -> None:
    """Double tap zooms only; single tap toggles the bar."""
    viewer.mouse.dblclick(*_CENTER)
    viewer.wait_for_timeout(_SETTLE_MS)
    assert "viewer-bar--hidden" not in viewer.eval_on_selector(".viewer-top", "e => e.className")


def test_swipe_navigates_only_at_fit(viewer: "playwright_api.Page") -> None:
    """Zoomed: drag pans, no navigation. Fit: drag swipes to next."""
    viewer.mouse.dblclick(*_CENTER)
    viewer.wait_for_timeout(_SETTLE_MS)
    _drag(viewer, -200)
    assert _position(viewer) == "1"

    viewer.mouse.dblclick(*_CENTER)
    viewer.wait_for_timeout(_SETTLE_MS)
    _drag(viewer, -200)
    assert _position(viewer) == "2"


def test_pinch_zooms(viewer: "playwright_api.Page") -> None:
    """Two fingers spreading apart zoom in."""
    cdp = viewer.context.new_cdp_session(viewer)
    x, y = _CENTER

    def touch(kind: str, spread: int) -> None:
        points = [{"id": 0, "x": x - spread, "y": y}, {"id": 1, "x": x + spread, "y": y}]
        cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points if spread else []})

    touch("touchStart", 20)
    for spread in range(30, 120, 10):
        touch("touchMove", spread)
    touch("touchEnd", 0)

    assert _scale(viewer) > 1
