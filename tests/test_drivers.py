"""Tests for media drivers."""
import shutil
from pathlib import Path

import pytest
from PIL import Image

from moments.drivers import images, videos
from moments.drivers.images import Rendition

from tests.conftest import create_test_video

_ORIENTATION_TAG = 274
_ROTATE_90_CW = 6


def _rotated_jpeg(path: Path) -> Path:
    """Stored 1600x800 (landscape); EXIF says display rotated → 800x1600 portrait."""
    exif = Image.Exif()
    exif[_ORIENTATION_TAG] = _ROTATE_90_CW
    Image.new("RGB", (1600, 800), (200, 50, 50)).save(path, exif=exif)
    return path


def _size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def test_renditions_apply_exif_orientation(tmp_path: Path) -> None:
    """Phone photos store pixels sideways + orientation tag; every output must be upright."""
    src = _rotated_jpeg(tmp_path / "phone.jpg")
    preview, thumb = tmp_path / "p.jpg", tmp_path / "t.jpg"

    assert images.create_renditions(src, [Rendition(preview, 800), Rendition(thumb, 200)])

    assert _size(preview) == (400, 800)
    assert _size(thumb) == (100, 200)


def test_renditions_any_target_order(tmp_path: Path) -> None:
    """Small target listed first still gets correct size (derived from largest)."""
    src = tmp_path / "plain.jpg"
    Image.new("RGB", (1600, 800)).save(src)
    preview, thumb = tmp_path / "p.jpg", tmp_path / "t.jpg"

    assert images.create_renditions(src, [Rendition(thumb, 200), Rendition(preview, 800)])

    assert _size(preview) == (800, 400)
    assert _size(thumb) == (200, 100)


def test_renditions_never_upscale(tmp_path: Path) -> None:
    """Source smaller than target keeps its size."""
    src = tmp_path / "small.jpg"
    Image.new("RGB", (300, 150)).save(src)
    preview = tmp_path / "p.jpg"

    assert images.create_renditions(src, [Rendition(preview, 800)])

    assert _size(preview) == (300, 150)


def test_renditions_unreadable_source(tmp_path: Path) -> None:
    """Corrupt file → False, no exception."""
    src = tmp_path / "bad.jpg"
    src.write_bytes(b"not an image")

    assert not images.create_renditions(src, [Rendition(tmp_path / "p.jpg", 800)])


def test_exif_dimensions_use_display_orientation(tmp_path: Path) -> None:
    """Reported width/height match how the photo is displayed."""
    src = _rotated_jpeg(tmp_path / "phone.jpg")

    exif = images.extract_exif(src)

    assert (exif["width"], exif["height"]) == (800, 1600)


_GPS_IFD = 0x8825


def _gps_jpeg(path: Path, lat_ref: str, lon_ref: str) -> Path:
    """JPEG with GPS 38°42'50" lat, 9°8'21" lon (Lisbon when N/W)."""
    exif = Image.Exif()
    exif.get_ifd(_GPS_IFD).update({
        1: lat_ref, 2: (38.0, 42.0, 50.0),
        3: lon_ref, 4: (9.0, 8.0, 21.0),
    })
    Image.new("RGB", (8, 8)).save(path, exif=exif)
    return path


def test_exif_gps_west_is_negative(tmp_path: Path) -> None:
    """Lisbon (N, W) → lon < 0; else link lands in the sea off Sardinia."""
    src = _gps_jpeg(tmp_path / "lisbon.jpg", "N", "W")

    gps = images.extract_exif(src)["gps"]

    assert isinstance(gps, dict)
    assert round(gps["lat"], 4) == 38.7139
    assert round(gps["lon"], 4) == -9.1392


def test_exif_gps_south_is_negative(tmp_path: Path) -> None:
    """S ref → lat < 0."""
    src = _gps_jpeg(tmp_path / "south.jpg", "S", "E")

    gps = images.extract_exif(src)["gps"]

    assert isinstance(gps, dict)
    assert gps["lat"] < 0
    assert gps["lon"] > 0


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_poster_overwrites_existing(tmp_path: Path) -> None:
    """Re-extract: stale poster exists → replaced, not ffmpeg "Overwrite? [y/N]" prompt (hang)."""
    assert create_test_video(tmp_path, "album")
    poster = tmp_path / "poster.jpg"
    poster.write_bytes(b"stale")

    assert videos.create_poster(tmp_path / "album" / "test_video.mp4", poster)

    width, height = _size(poster)  # Raises if still the stale bytes.
    assert width * 3 == height * 4
