"""Viewer behavior in real Chrome against a live server (skipped if Playwright/Chrome absent)."""
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


def test_arrows_leave_close_unfocused(base_url: str) -> None:
    """← → navigate without putting focus on the close button."""
    with playwright_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except playwright_api.Error:
            pytest.skip("chrome not installed")

        page = browser.new_page()
        first = _extract(page, base_url)
        page.goto(f"{base_url}/#/a/{_ALBUM}/m/{first}")
        page.wait_for_selector(".viewer-media", timeout=_TIMEOUT_MS)

        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowLeft")

        close_focused = page.eval_on_selector(".viewer-close", "e => e === document.activeElement")
        browser.close()

    assert not close_focused
