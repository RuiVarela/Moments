"""Read-only album scanning."""
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

# Image and video extensions (lowercase).
_IMAGE_EXTS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".gif",
}
_VIDEO_EXTS: set[str] = {
    ".mp4",
    ".webm",
    ".mov",
    ".avi",  # Served as-is; most browsers can't play it.
}


def list_albums(source_dir: Path) -> list[str]:
    """List album names (root-level folder names) in source_dir.

    Skips hidden folders (prefix .).
    """
    albums: list[str] = []
    try:
        for item in source_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                albums.append(item.name)
    except OSError as e:
        _logger.error(f"Failed to list albums in {source_dir}: {e}")
        return []
    return sorted(albums)


def scan_album(album_path: Path) -> list[dict[str, object]]:
    """Scan album recursively, return list of media items (relative paths + type).

    Skips:
    - Hidden files/folders (prefix .)
    - Symlinks

    Returns list of dicts: {path: Path (relative), type: "image"|"video"}
    """
    items: list[dict[str, object]] = []

    if not album_path.is_dir():
        return items

    try:
        for entry in album_path.rglob("*"):
            # Skip symlinks, hidden items.
            if entry.is_symlink() or entry.name.startswith("."):
                continue

            if not entry.is_file():
                continue

            # Get relative path and extension.
            rel_path = entry.relative_to(album_path)
            ext = entry.suffix.lower()

            if ext in _IMAGE_EXTS:
                items.append({"path": str(rel_path), "type": "image"})
            elif ext in _VIDEO_EXTS:
                items.append({"path": str(rel_path), "type": "video"})

    except OSError as e:
        _logger.error(f"Failed to scan album {album_path}: {e}")

    return items
