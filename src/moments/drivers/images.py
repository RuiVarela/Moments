"""Image processing: EXIF, GPS, resize."""
import logging
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import NamedTuple, Optional

from PIL import Image, ImageOps
from PIL.ExifTags import GPSTAGS, TAGS

from moments.types import MediaItemDict

_logger = logging.getLogger(__name__)

_ORIENTATION_TAG = 274

# EXIF orientations that rotate 90°/270° → displayed width/height swap.
_TRANSPOSED_ORIENTATIONS = {5, 6, 7, 8}


def extract_exif(image_path: Path) -> MediaItemDict:
    """Extract EXIF data from image.

    Returns dict with:
    - date (Unix timestamp) or None
    - gps {"lat", "lon"} or None
    - width, height
    """
    result: MediaItemDict = {
        "date": None,
        "gps": None,
        "width": None,
        "height": None,
    }

    try:
        with Image.open(image_path) as img:
            result["width"] = img.width
            result["height"] = img.height

            exif = img.getexif()
            if not exif:
                return result

            # Phone photos: pixels stored sideways + orientation tag; report displayed size.
            if exif.get(_ORIENTATION_TAG) in _TRANSPOSED_ORIENTATIONS:
                result["width"], result["height"] = img.height, img.width

            # Extract DateTimeOriginal (tag 36867).
            date_str = exif.get(36867) or exif.get(306)  # Fallback to DateTime.
            if date_str:
                try:
                    dt = datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
                    result["date"] = int(dt.timestamp())
                except ValueError:
                    pass

            # Extract GPS (tag 34853).
            gps_ifd = exif.get_ifd(0x8825)  # IFD tag for GPS.
            if gps_ifd:
                gps_data = _parse_gps_ifd(gps_ifd)
                if gps_data:
                    result["gps"] = gps_data

    except Exception as e:
        _logger.warning(f"Failed to extract EXIF from {image_path}: {e}")

    return result


def _parse_gps_ifd(gps_ifd: dict[int, object]) -> Optional[dict[str, float]]:
    """Parse GPS IFD into {lat, lon}."""
    try:
        lat_ref = gps_ifd.get(1)
        lat_data = gps_ifd.get(2)
        lon_ref = gps_ifd.get(3)
        lon_data = gps_ifd.get(4)

        if not (lat_data and lon_data):
            return None

        lat = _dms_to_decimal(lat_data)
        lon = _dms_to_decimal(lon_data)

        if lat is None or lon is None:
            return None

        if _gps_ref(lat_ref) == "S":
            lat = -lat
        if _gps_ref(lon_ref) == "W":
            lon = -lon

        return {"lat": lat, "lon": lon}
    except (ValueError, TypeError):
        return None


# Pillow yields refs as str ("W"); some writers store bytes (b"W").
def _gps_ref(ref: object) -> str:
    if isinstance(ref, bytes):
        return ref.decode("ascii", "ignore").strip("\x00 ")
    return str(ref or "").strip("\x00 ")


def _dms_to_decimal(dms: object) -> Optional[float]:
    """Convert degrees/minutes/seconds (tuple of Fractions) to decimal."""
    if not isinstance(dms, (list, tuple)) or len(dms) < 2:
        return None
    try:
        d = float(dms[0])
        m = float(dms[1]) / 60.0
        s = float(dms[2] if len(dms) > 2 else 0) / 3600.0
        return d + m + s
    except (ValueError, TypeError, ZeroDivisionError):
        return None


class Rendition(NamedTuple):
    """Output square JPEG + max side length (px) + JPEG quality (1..95)."""

    path: Path
    max_size: int
    quality: int


def create_renditions(src_path: Path, renditions: list[Rendition]) -> bool:
    """Decode source once; write every rendition (center-cropped square), each resized from the previous.

    4000x3000 JPEG ─draft─► 1066x800 ─crop+resize─► 800x800 ─rotate─► preview.jpg
                                                       └─resize─► 200x200 ─► thumb.jpg
    """
    if not renditions:
        return True

    largest_first = sorted(renditions, key=lambda r: r.max_size, reverse=True)

    try:
        with Image.open(src_path) as img:
            _draft(img, largest_first[0].max_size)

            # Rotate after shrinking: far fewer pixels. Center square crop is rotation-invariant.
            # Output JPEG has no orientation tag.
            current = ImageOps.exif_transpose(_square(img, largest_first[0].max_size))

            for rendition in largest_first:
                current = _square(current, rendition.max_size)
                rendition.path.parent.mkdir(parents=True, exist_ok=True)
                current.save(rendition.path, "JPEG", quality=rendition.quality)

        return True
    except Exception as e:
        _logger.warning(f"Failed to create renditions for {src_path}: {e}")
        return False


def _draft(img: Image.Image, max_size: int) -> None:
    """JPEG only: decode at 1/2, 1/4 or 1/8 scale, shorter side still >= target. No-op otherwise.

    Example: 4000x3000 → 800 target → decodes 1000x750 instead of 12 MP.
    """
    scale = max_size / min(img.size)
    if scale >= 1:
        return

    img.draft(None, (ceil(img.width * scale), ceil(img.height * scale)))


def _square(img: Image.Image, max_size: int) -> Image.Image:
    """Center-crop to square, shrink to max_size; never upscale.

    Example: 1600x800, 200 → crop 800x800 (drop 400px each side) → 200x200.
    """
    side = min(*img.size, max_size)
    return ImageOps.fit(img, (side, side), Image.Resampling.LANCZOS)
