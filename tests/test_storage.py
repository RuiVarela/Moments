"""Tests for storage layer (source scanning, index, data)."""
from pathlib import Path

import pytest

from moments.storage import data, source
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
    assert all("photo_" in item["path"] for item in items)


def test_scan_album_skips_root_files(tmp_albums_dir: Path) -> None:
    """Test that root files are skipped."""
    album_path = tmp_albums_dir / "album"
    album_path.mkdir()

    # Root file (should be skipped).
    from PIL import Image

    img = Image.new("RGB", (100, 100))
    root_img = album_path / "root.jpg"
    img.save(str(root_img))

    # Nested file (should be included).
    subfolder = album_path / "sub"
    subfolder.mkdir()
    nested_img = subfolder / "nested.jpg"
    img.save(str(nested_img))

    items = source.scan_album(album_path)
    assert len(items) == 1
    assert "nested.jpg" in items[0]["path"]


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

    items = [
        {
            "hash": "abc123",
            "path": "subfolder/photo.jpg",
            "type": "image",
            "mtime": 1000,
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
    items1 = [{"hash": "v1", "path": "file1.jpg", "type": "image"}]
    data.save_index(index_path, items1)

    # Overwrite.
    items2 = [{"hash": "v2", "path": "file2.jpg", "type": "image"}]
    data.save_index(index_path, items2)

    # Load and verify it's v2.
    loaded = data.load_index(index_path)
    assert loaded is not None
    assert loaded[0]["hash"] == "v2"
