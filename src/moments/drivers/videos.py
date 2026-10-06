"""Video processing: metadata, poster extraction."""
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from moments.types import MediaItemDict

_logger = logging.getLogger(__name__)


def extract_video_info(
    video_path: Path,
) -> MediaItemDict:
    """Extract video metadata using ffprobe.

    Returns dict with:
    - date (Unix timestamp) or None
    - width, height
    - duration (seconds)
    - codec
    """
    result: MediaItemDict = {
        "date": None,
        "width": None,
        "height": None,
        "duration": None,
        "codec": None,
    }

    try:
        info = _ffprobe(video_path)
        if not info:
            return result

        # Extract video stream info.
        streams = info.get("streams", [])
        video_stream = next(
            (s for s in streams if s.get("codec_type") == "video"), None
        )

        if video_stream:
            result["width"] = video_stream.get("width")
            result["height"] = video_stream.get("height")
            result["duration"] = float(
                video_stream.get("duration", 0) or 0
            )
            result["codec"] = video_stream.get("codec_name")

        # Extract creation date from format tags or stream tags.
        format_tags = info.get("format", {}).get("tags", {})
        stream_tags = video_stream.get("tags", {}) if video_stream else {}

        for key in ["creation_time", "date"]:
            date_str = format_tags.get(key) or stream_tags.get(key)
            if date_str:
                ts = _iso_to_timestamp(str(date_str))
                if ts is not None:
                    result["date"] = ts
                    break

    except Exception as e:
        _logger.warning(f"Failed to extract video info from {video_path}: {e}")

    return result


def _ffprobe(video_path: Path) -> Optional[dict[str, Any]]:
    """Run ffprobe and return JSON info dict."""
    try:
        output = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if output.returncode == 0:
            info: dict[str, Any] = json.loads(output.stdout)
            return info
    except FileNotFoundError:
        _logger.debug("ffprobe not found; video metadata unavailable")
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return None


def _iso_to_timestamp(iso_str: str) -> Optional[int]:
    """Convert ISO 8601 to Unix timestamp."""
    import datetime

    try:
        # Handle "2024-01-15T10:30:00Z" or similar.
        dt_str = iso_str.split("+")[0].split(".")[0]
        dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except ValueError:
        return None


def create_poster(
    video_path: Path, poster_path: Path, max_size: int = 800
) -> bool:
    """Extract first keyframe as poster using ffmpeg.

    Fallback to 1-second mark if no keyframe found.
    """
    # Center-crop to square, shrink to max_size; never upscale. 640x480 → 480x480.
    square = f"crop=min(iw\\,ih):min(iw\\,ih),scale=min(iw\\,{max_size}):-1"

    try:
        poster_path.parent.mkdir(parents=True, exist_ok=True)

        # Try to get first keyframe.
        subprocess.run(
            [
                "ffmpeg",
                "-y",  # Overwrite stale poster; else prompt blocks.
                "-v",
                "quiet",
                "-i",
                str(video_path),
                "-vf",
                f"select=eq(pict_type\\,I),{square}",
                "-vframes",
                "1",
                str(poster_path),
            ],
            timeout=10,
            check=False,
        )

        # Fallback: if no poster created, try 1-second mark.
        if not poster_path.exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "quiet",
                    "-ss",
                    "1",
                    "-i",
                    str(video_path),
                    "-vf",
                    square,
                    "-vframes",
                    "1",
                    str(poster_path),
                ],
                timeout=10,
                check=False,
            )

        return poster_path.exists()

    except Exception as e:
        _logger.warning(f"Failed to create poster for {video_path}: {e}")
        return False
