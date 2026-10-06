"""Tests for media drivers."""
import shutil
from pathlib import Path

import pytest
from PIL import Image

from moments.drivers import images, videos
from moments.drivers.images import Rendition

from tests.conftest import create_test_video

_ORIENTATION_TAG = 274
_QUALITY = 60
_ROTATE_90_CW = 6


_RED = (255, 0, 0)
_BLUE = (0, 0, 255)


def _rotated_jpeg(path: Path) -> Path:
    """Stored 1600x800 (landscape, left red / right blue); EXIF says display rotated → 800x1600 portrait."""
    img = Image.new("RGB", (1600, 800), _RED)
    img.paste(_BLUE, (800, 0, 1600, 800))

    exif = Image.Exif()
    exif[_ORIENTATION_TAG] = _ROTATE_90_CW
    img.save(path, exif=exif)
    return path


def _near(pixel: tuple[int, ...], color: tuple[int, int, int]) -> bool:
    """JPEG is lossy; compare with tolerance."""
    return all(abs(a - b) < 40 for a, b in zip(pixel, color))


def _pixel(path: Path, xy: tuple[int, int]) -> tuple[int, ...]:
    with Image.open(path) as img:
        pixel = img.convert("RGB").getpixel(xy)

    assert isinstance(pixel, tuple)  # RGB → (r, g, b).
    return pixel


def _size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def test_renditions_apply_exif_orientation(tmp_path: Path) -> None:
    """Phone photos store pixels sideways + orientation tag; every output must be upright.

    Stored red|blue, rotated 90° CW → red on top, blue at bottom.
    """
    src = _rotated_jpeg(tmp_path / "phone.jpg")
    preview, thumb = tmp_path / "p.jpg", tmp_path / "t.jpg"

    assert images.create_renditions(src, [Rendition(preview, 800, _QUALITY), Rendition(thumb, 200, _QUALITY)])

    assert _near(_pixel(thumb, (100, 10)), _RED)
    assert _near(_pixel(thumb, (100, 190)), _BLUE)


def test_renditions_square(tmp_path: Path) -> None:
    """Any aspect → square of max_size; small target listed first still correct."""
    src = tmp_path / "plain.jpg"
    Image.new("RGB", (1600, 800)).save(src)
    preview, thumb = tmp_path / "p.jpg", tmp_path / "t.jpg"

    assert images.create_renditions(src, [Rendition(thumb, 200, _QUALITY), Rendition(preview, 800, _QUALITY)])

    assert _size(preview) == (800, 800)
    assert _size(thumb) == (200, 200)


def test_renditions_center_crop(tmp_path: Path) -> None:
    """1200x400: red | blue | red thirds → square keeps only the blue center."""
    src = tmp_path / "wide.png"
    img = Image.new("RGB", (1200, 400), _RED)
    img.paste(_BLUE, (400, 0, 800, 400))
    img.save(src)
    thumb = tmp_path / "t.jpg"

    assert images.create_renditions(src, [Rendition(thumb, 200, _QUALITY)])

    assert _near(_pixel(thumb, (2, 100)), _BLUE)
    assert _near(_pixel(thumb, (197, 100)), _BLUE)


def test_renditions_never_upscale(tmp_path: Path) -> None:
    """Source shorter side below target → square of shorter side."""
    src = tmp_path / "small.jpg"
    Image.new("RGB", (300, 150)).save(src)
    preview = tmp_path / "p.jpg"

    assert images.create_renditions(src, [Rendition(preview, 800, _QUALITY)])

    assert _size(preview) == (150, 150)


def test_renditions_quality(tmp_path: Path) -> None:
    """Rendition quality reaches the encoder: lower quality → smaller file."""
    src = tmp_path / "noise.png"
    Image.effect_noise((400, 400), 64).convert("RGB").save(src)
    low, high = tmp_path / "low.jpg", tmp_path / "high.jpg"

    assert images.create_renditions(src, [Rendition(low, 200, 30)])
    assert images.create_renditions(src, [Rendition(high, 200, 90)])

    assert low.stat().st_size < high.stat().st_size


def test_renditions_unreadable_source(tmp_path: Path) -> None:
    """Corrupt file → False, no exception."""
    src = tmp_path / "bad.jpg"
    src.write_bytes(b"not an image")

    assert not images.create_renditions(src, [Rendition(tmp_path / "p.jpg", 800, _QUALITY)])


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

    _size(poster)  # Raises if still the stale bytes.


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_poster_square(tmp_path: Path) -> None:
    """640x480 video → 480x480 center crop (never upscaled to 800)."""
    assert create_test_video(tmp_path, "album")
    poster = tmp_path / "poster.jpg"

    assert videos.create_poster(tmp_path / "album" / "test_video.mp4", poster, 800)

    assert _size(poster) == (480, 480)
