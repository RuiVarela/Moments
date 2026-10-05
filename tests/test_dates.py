"""Date fallback (filename) and date sorting; no mtime anywhere."""
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from moments.app import create_app
from moments.config import Config
from moments.drivers import filenames
from moments.storage import data

_EXIF_DATETIME_TAG = 306


def _ts(*args: int) -> int:
    """Naive local timestamp, same convention as EXIF dates."""
    return int(datetime(*args).timestamp())


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("2006-03-03_00001.jpg", _ts(2006, 3, 3)),
        ("2024-12-31_12345.MOV", _ts(2024, 12, 31)),
        ("2006-03-03.jpg", _ts(2006, 3, 3)),
        ("IMG_1234.jpg", None),
        ("2006-13-45_00001.jpg", None),
        ("photo 2006-03-03.jpg", None),
    ],
)
def test_date_from_name(name: str, expected: int | None) -> None:
    """'YYYY-MM-DD_NNNNN.ext' → that day; anything else → None."""
    assert filenames.date_from_name(name) == expected


def _client(config: Config) -> TestClient:
    return TestClient(create_app(config))


def _wait_idle(client: TestClient, album: str) -> None:
    for _ in range(50):
        if client.get(f"/api/albums/{album}/extract/status").json()["status"] != "running":
            return
        time.sleep(0.05)


def test_extraction_uses_filename_date(config: Config, tmp_albums_dir: Path) -> None:
    """No EXIF date → date parsed from filename; no mtime stored."""
    album = tmp_albums_dir / "flat"
    album.mkdir()
    Image.new("RGB", (50, 50)).save(album / "2006-03-03_00001.jpg")

    client = _client(config)
    client.get("/api/albums/flat")
    _wait_idle(client, "flat")

    item = client.get("/api/albums/flat").json()["items"][0]
    assert item["date"] == _ts(2006, 3, 3)
    assert "mtime" not in item


def test_exif_date_wins_over_filename(config: Config, tmp_albums_dir: Path) -> None:
    """EXIF date present → filename ignored."""
    album = tmp_albums_dir / "exif"
    album.mkdir()
    exif = Image.Exif()
    exif[_EXIF_DATETIME_TAG] = "2010:05:06 07:08:09"
    Image.new("RGB", (50, 50)).save(album / "2006-03-03_00001.jpg", exif=exif)

    client = _client(config)
    client.get("/api/albums/exif")
    _wait_idle(client, "exif")

    item = client.get("/api/albums/exif").json()["items"][0]
    assert item["date"] == _ts(2010, 5, 6, 7, 8, 9)


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_undated_items_sort_last(config: Config, tmp_albums_dir: Path, order: str) -> None:
    """Sort by date: undated after dated in both directions, by name among themselves."""
    (tmp_albums_dir / "mixed").mkdir()
    items = [
        {"hash": "b", "path": "b.jpg", "type": "image", "size": 1, "date": None},
        {"hash": "old", "path": "old.jpg", "type": "image", "size": 1, "date": 100},
        {"hash": "a", "path": "a.jpg", "type": "image", "size": 1, "date": None},
        {"hash": "new", "path": "new.jpg", "type": "image", "size": 1, "date": 200},
    ]
    data.save_index(data.album_index_path(config.data_dir, "mixed"), items)  # type: ignore[arg-type]

    resp = _client(config).get(f"/api/albums/mixed?sort=date&order={order}").json()
    hashes = [i["hash"] for i in resp["items"]]

    dated = ["old", "new"] if order == "asc" else ["new", "old"]
    assert hashes == dated + ["a", "b"]


def test_mtime_sort_rejected(config: Config, tmp_albums_dir: Path) -> None:
    """mtime is no longer a sort option."""
    (tmp_albums_dir / "x").mkdir()
    assert _client(config).get("/api/albums/x?sort=mtime").status_code == 400
