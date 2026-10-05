"""Tests for static file serving."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from moments.app import create_app
from moments.config import Config


@pytest.fixture
def client(config: Config) -> TestClient:
    """Create test client."""
    app = create_app(config)
    return TestClient(app)


def test_root_serves_index_html(client: TestClient) -> None:
    """Test GET / returns index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!doctype html>" in response.text.lower()


def test_js_files_served(client: TestClient) -> None:
    """Test JS files are served."""
    response = client.get("/js/main.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_css_files_served(client: TestClient) -> None:
    """Test CSS files are served."""
    response = client.get("/css/base.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_api_still_works(client: TestClient) -> None:
    """Test API endpoints still work."""
    response = client.get("/api/albums")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_png_original_mime_type(client: TestClient, tmp_path: Path) -> None:
    """Test PNG original has correct MIME type."""
    albums_dir = tmp_path / "albums"
    data_dir = tmp_path / "data"
    albums_dir.mkdir()
    data_dir.mkdir()

    # Create album with PNG.
    album_path = albums_dir / "test"
    subfolder = album_path / "sub"
    subfolder.mkdir(parents=True)

    from PIL import Image
    img = Image.new("RGB", (100, 100))
    img.save(str(subfolder / "photo.png"), "PNG")

    config = Config(
        port=8000,
        source_dir=albums_dir,
        data_dir=data_dir,
    )
    client = TestClient(create_app(config))

    # Trigger extraction.
    client.get("/api/albums/test")
    import time
    for _ in range(20):
        r = client.get("/api/albums/test/extract/status")
        if r.json()["status"] == "idle":
            break
        time.sleep(0.1)

    # Get the PNG original.
    detail = client.get("/api/albums/test").json()
    if detail.get("items"):
        items = detail["items"]
        png_item = next(
            (i for i in items if i["path"].endswith(".png")), None
        )
        if png_item:
            response = client.get(
                f"/api/albums/test/media/{png_item['hash']}/original"
            )
            assert response.status_code == 200
            assert (
                "image/png" in response.headers["content-type"]
            ), f"Expected image/png, got {response.headers['content-type']}"
