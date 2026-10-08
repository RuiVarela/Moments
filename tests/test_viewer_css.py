"""Viewer CSS checks in real Chrome (skipped if Playwright/Chrome absent)."""
from pathlib import Path

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

_CSS_DIR = Path(__file__).parent.parent / "src" / "moments" / "static" / "css"
_CSS_FILES = ("tokens.css", "base.css", "viewer.css")
_BAR_DURATION = "0.5s"


def _bar_duration(reduced_motion: str) -> str:
    """Computed transition-duration of the viewer top bar."""
    css = "\n".join((_CSS_DIR / name).read_text() for name in _CSS_FILES)
    html = f"<style>{css}</style><div class='viewer-top'></div>"

    with playwright_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except playwright_api.Error:
            pytest.skip("chrome not installed")

        page = browser.new_page(reduced_motion=reduced_motion)
        page.set_content(html)
        duration: str = page.eval_on_selector(
            ".viewer-top", "e => getComputedStyle(e).transitionDuration"
        )
        browser.close()
    return duration


@pytest.mark.parametrize("reduced_motion", ["no-preference", "reduce"])
def test_bar_slides(reduced_motion: str) -> None:
    """Bar show/hide animates, even with OS reduced motion on."""
    assert _bar_duration(reduced_motion) == _BAR_DURATION
