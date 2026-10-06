"""Tests for storage layer (source scanning, index, data)."""
from pathlib import Path

import pytest

from moments.storage import data, source
from moments.types import MediaItemDict
from tests.conftest import create_test_album


def test_list_albums(tmp_albums_dir: Path) -> None:
    """Test listing albums."""
    create_test_album(tmp_albums_dir, "album1")
    create_test_album(tmp_albums_dir, "album2")

    # Hidden album should be skipped.
    (tmp_albums_dir / ".hidden").mkdir()

    albums = source.list_albums(tmp_albums_dir)
    assert albums == ["album1", "album2"]


def test_scan_album(tmp_albums_dir: Path) -> None:
    """Test scanning album."""
    album_path = create_test_album(tmp_albums_dir, "vacation")

    items = source.scan_album(album_path)

    # Should find 3 images in subfolder, skip root files and hidden.
    assert len(items) == 3
    assert all(item["type"] == "image" for item in items)
    assert all("photo_" in str(item["path"]) for item in items)


def test_scan_album_includes_album_root_files(tmp_albums_dir: Path) -> None:
    """Files directly in the album folder belong to the album (e.g. flat albums, cover.jpg)."""
    album_path = tmp_albums_dir / "album"
    album_path.mkdir()

    from PIL import Image

    img = Image.new("RGB", (100, 100))
    img.save(str(album_path / "root.jpg"))

    subfolder = album_path / "sub"
    subfolder.mkdir()
    img.save(str(subfolder / "nested.jpg"))

    paths = sorted(str(item["path"]) for item in source.scan_album(album_path))
    assert paths == ["root.jpg", "sub/nested.jpg"]


def test_scan_album_includes_avi_as_video(tmp_albums_dir: Path) -> None:
    """AVI files are indexed as video (served as-is, no transcoding)."""
    album_path = tmp_albums_dir / "album"
    album_path.mkdir()
    (album_path / "clip.AVI").write_bytes(b"")

    assert source.scan_album(album_path) == [{"path": "clip.AVI", "type": "video"}]


def test_list_albums_ignores_source_root_files(tmp_albums_dir: Path) -> None:
    """Loose files in source_dir belong to no album."""
    (tmp_albums_dir / "loose.jpg").write_bytes(b"")
    (tmp_albums_dir / "album").mkdir()

    assert source.list_albums(tmp_albums_dir) == ["album"]


def test_media_hash_stable(tmp_albums_dir: Path) -> None:
    """Test that media hash is stable across runs."""
    path = Path("subfolder/photo_001.jpg")

    hash1 = data.media_hash(path)
    hash2 = data.media_hash(path)

    assert hash1 == hash2
    assert len(hash1) == 16


def test_save_and_load_index(tmp_data_dir: Path) -> None:
    """Test saving and loading index."""
    index_path = tmp_data_dir / "album" / "index.json"

    items: list[MediaItemDict] = [
        {
            "hash": "abc123",
            "path": "subfolder/photo.jpg",
            "type": "image",
            "size": 50000,
            "date": 1705000000,
            "gps": {"lat": 37.7749, "lon": -122.4194},
            "width": 800,
            "height": 600,
            "duration": None,
            "codec": None,
        }
    ]

    # Save.
    assert data.save_index(index_path, items) is True

    # Load.
    loaded = data.load_index(index_path)
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0]["hash"] == "abc123"


def test_index_atomic_write(tmp_data_dir: Path) -> None:
    """Test that index write is atomic (tmp + rename)."""
    index_path = tmp_data_dir / "album" / "index.json"

    # Write initial.
    items1: list[MediaItemDict] = [{"hash": "v1", "path": "file1.jpg", "type": "image"}]
    data.save_index(index_path, items1)

    # Overwrite.
    items2: list[MediaItemDict] = [{"hash": "v2", "path": "file2.jpg", "type": "image"}]
    data.save_index(index_path, items2)

    # Load and verify it's v2.
    loaded = data.load_index(index_path)
    assert loaded is not None
    assert loaded[0]["hash"] == "v2"
