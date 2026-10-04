"""Image processing: EXIF, GPS, resize."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from moments.types import MediaItemDict

_logger = logging.getLogger(__name__)


def extract_exif(image_path: Path) -> dict[str, object]:
    """Extract EXIF data from image.

    Returns dict with:
    - date (Unix timestamp) or None
    - gps {"lat", "lon"} or None
    - width, height
    """
    result: dict[str, object] = {
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

        if lat_ref == b"S":
            lat = -lat
        if lon_ref == b"W":
            lon = -lon

        return {"lat": lat, "lon": lon}
    except (ValueError, TypeError):
        return None


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


def create_thumbnail(
    src_path: Path, thumb_path: Path, max_size: int
) -> bool:
    """Create thumbnail, return True on success."""
    try:
        with Image.open(src_path) as img:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumb_path, "JPEG", quality=85)
        return True
    except Exception as e:
        _logger.warning(f"Failed to create thumbnail {thumb_path}: {e}")
        return False
