"""Integration tests for API endpoints."""
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from moments.app import create_app
from moments.config import Config
from tests.conftest import create_test_album


@pytest.fixture
def client(config: Config) -> TestClient:
    """Create test client."""
    app = create_app(config)
    return TestClient(app)


def test_list_albums_empty(client: TestClient, tmp_albums_dir: Path) -> None:
    """Test listing albums when none exist."""
    response = client.get("/api/albums")
    assert response.status_code == 200
    assert response.json() == []


def test_list_albums_with_albums(
    client: TestClient, tmp_albums_dir: Path
) -> None:
    """Test listing albums."""
    create_test_album(tmp_albums_dir, "vacation")
    create_test_album(tmp_albums_dir, "beach")

    response = client.get("/api/albums")
    assert response.status_code == 200

    albums = response.json()
    assert len(albums) == 2
    ids = [a["id"] for a in albums]
    assert "beach" in ids
    assert "vacation" in ids


def test_get_album_not_found(client: TestClient) -> None:
    """Test getting non-existent album."""
    response = client.get("/api/albums/nonexistent")
    assert response.status_code == 404


def test_get_album_detail(
    client: TestClient, album_with_images: Path
) -> None:
    """Test getting album detail (triggers extraction)."""
    response = client.get("/api/albums/vacation")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "vacation"
    # Cover might be null if not extracted yet, or have a value.
    assert "cover" in data
    assert "status" in data


def test_extraction_status_initially_idle(
    client: TestClient, album_empty: Path
) -> None:
    """Test extraction status starts as idle."""
    response = client.get("/api/albums/empty/extract/status")
    assert response.status_code == 200

    status = response.json()
    assert status["status"] in ["idle", "running"]
    assert status["done"] == 0
    assert status["total"] == 0


def test_start_extraction(
    client: TestClient, album_with_images: Path
) -> None:
    """Test starting extraction."""
    response = client.post("/api/albums/vacation/extract")
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_start_extraction_nonexistent(client: TestClient) -> None:
    """Test starting extraction for non-existent album."""
    response = client.post("/api/albums/nonexistent/extract")
    assert response.status_code == 404


def test_get_thumb_not_found(client: TestClient) -> None:
    """Test getting thumbnail before extraction."""
    response = client.get("/api/albums/vacation/media/abc123/thumb")
    assert response.status_code == 404


def test_invalid_sort_param(client: TestClient, album_with_images: Path) -> None:
    """Test invalid sort parameter."""
    response = client.get(
        "/api/albums/vacation?sort=invalid&order=asc"
    )
    assert response.status_code == 400


def test_valid_sort_params(
    client: TestClient, album_with_images: Path
) -> None:
    """Test valid sort parameters."""
    response = client.get(
        "/api/albums/vacation?sort=date&order=asc"
    )
    assert response.status_code == 200

    response = client.get(
        "/api/albums/vacation?sort=name&order=desc"
    )
    assert response.status_code == 200


def _extracted(client: TestClient, album_id: str) -> dict[str, Any]:
    """Run extraction to completion, return album detail."""
    client.post(f"/api/albums/{album_id}/extract")
    for _ in range(250):
        if client.get(f"/api/albums/{album_id}/extract/status").json()["status"] != "running":
            break
        time.sleep(0.02)
    detail: dict[str, Any] = client.get(f"/api/albums/{album_id}").json()
    return detail


def test_set_cover(client: TestClient, album_with_images: Path) -> None:
    """Chosen item becomes cover in detail and list."""
    album = _extracted(client, "vacation")
    chosen = next(i for i in album["items"] if i["hash"] != album["cover_hash"])["hash"]

    response = client.put("/api/albums/vacation/cover", json={"hash": chosen})

    assert response.status_code == 200
    assert client.get("/api/albums/vacation").json()["cover_hash"] == chosen
    listed = client.get("/api/albums").json()[0]
    assert listed["cover_hash"] == chosen
    assert chosen in listed["cover"]


def test_set_cover_unknown_hash(client: TestClient, album_with_images: Path) -> None:
    """Hash not in album → 404, cover unchanged."""
    before = _extracted(client, "vacation")["cover_hash"]

    response = client.put("/api/albums/vacation/cover", json={"hash": "nope"})

    assert response.status_code == 404
    assert client.get("/api/albums/vacation").json()["cover_hash"] == before


def test_set_cover_unknown_album(client: TestClient) -> None:
    response = client.put("/api/albums/nonexistent/cover", json={"hash": "x"})
    assert response.status_code == 404


def test_cover_survives_reextract(client: TestClient, album_with_images: Path) -> None:
    """Re-extraction rewrites index; chosen cover kept."""
    album = _extracted(client, "vacation")
    chosen = album["items"][-1]["hash"]
    client.put("/api/albums/vacation/cover", json={"hash": chosen})

    assert _extracted(client, "vacation")["cover_hash"] == chosen
