"""Tests for media drivers."""
from pathlib import Path

from PIL import Image

from moments.drivers import images

_ORIENTATION_TAG = 274
_ROTATE_90_CW = 6


def _rotated_jpeg(path: Path) -> Path:
    """Stored 400x200 (landscape); EXIF says display rotated → 200x400 portrait."""
    exif = Image.Exif()
    exif[_ORIENTATION_TAG] = _ROTATE_90_CW
    Image.new("RGB", (400, 200), (200, 50, 50)).save(path, exif=exif)
    return path


def test_thumbnail_applies_exif_orientation(tmp_path: Path) -> None:
    """Phone photos store pixels sideways + orientation tag; thumbs must be upright."""
    src = _rotated_jpeg(tmp_path / "phone.jpg")
    thumb = tmp_path / "thumb.jpg"

    assert images.create_thumbnail(src, thumb, 200)

    with Image.open(thumb) as img:
        assert img.size == (100, 200)


def test_exif_dimensions_use_display_orientation(tmp_path: Path) -> None:
    """Reported width/height match how the photo is displayed."""
    src = _rotated_jpeg(tmp_path / "phone.jpg")

    exif = images.extract_exif(src)

    assert (exif["width"], exif["height"]) == (200, 400)


def test_thumbnail_without_orientation_unchanged(tmp_path: Path) -> None:
    """No orientation tag → keep stored orientation."""
    src = tmp_path / "plain.jpg"
    Image.new("RGB", (400, 200)).save(src)
    thumb = tmp_path / "thumb.jpg"

    assert images.create_thumbnail(src, thumb, 200)

    with Image.open(thumb) as img:
        assert img.size == (200, 100)
