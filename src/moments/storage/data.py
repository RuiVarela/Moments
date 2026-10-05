"""Index and derived file storage."""
import json
import logging
import tempfile
from hashlib import sha1
from pathlib import Path
from typing import Optional

from moments.types import AlbumIndexDict, MediaItemDict

_logger = logging.getLogger(__name__)
_INDEX_VERSION = 1


def album_index_path(data_dir: Path, album_id: str) -> Path:
    """Path to album's index.json."""
    return data_dir / album_id / "index.json"


def load_index(index_path: Path) -> Optional[list[MediaItemDict]]:
    """Load and parse index.json, return items list or None on error."""
    try:
        if not index_path.exists():
            return None

        with open(index_path) as f:
            data: dict[str, object] = json.load(f)

        if data.get("version") != _INDEX_VERSION:
            _logger.warning(f"Index version mismatch: {index_path}")
            return None

        items: list[MediaItemDict] = data.get("items", [])
        return items

    except Exception as e:
        _logger.error(f"Failed to load index {index_path}: {e}")
        return None


def load_cover(index_path: Path) -> Optional[str]:
    """User-chosen cover hash from index.json, or None."""
    try:
        with open(index_path) as f:
            cover = json.load(f).get("cover")
        return cover if isinstance(cover, str) else None
    except Exception:
        return None


def save_cover(index_path: Path, cover: str) -> bool:
    """Set cover hash in existing index.json (items untouched)."""
    items = load_index(index_path)
    if items is None:
        return False
    return save_index(index_path, items, cover)


def save_index(
    index_path: Path, items: list[MediaItemDict], cover: Optional[str] = None
) -> bool:
    """Write index.json atomically (tmp + rename)."""
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)

        index_data: AlbumIndexDict = {
            "version": _INDEX_VERSION,
            "items": items,
        }
        if cover:
            index_data["cover"] = cover

        # Write to temp file, then rename (atomic).
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=index_path.parent,
            delete=False,
            suffix=".tmp",
        ) as f:
            json.dump(index_data, f)
            temp_path = Path(f.name)

        temp_path.replace(index_path)
        return True

    except Exception as e:
        _logger.error(f"Failed to save index {index_path}: {e}")
        return False


def thumb_path(data_dir: Path, album_id: str, item_hash: str) -> Path:
    """Path to thumbnail file."""
    return data_dir / album_id / "thumbs" / f"{item_hash}.jpg"


def preview_path(data_dir: Path, album_id: str, item_hash: str) -> Path:
    """Path to preview file."""
    return data_dir / album_id / "previews" / f"{item_hash}.jpg"


def media_hash(rel_path: Path) -> str:
    """Compute stable hash for relative path: sha1[:16]."""
    return sha1(str(rel_path).encode()).hexdigest()[:16]
