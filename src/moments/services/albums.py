"""Album operations: list, detail, sorting, cover selection."""
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from moments.config import Config
from moments.storage import data, source
from moments.types import AlbumListItemDict, MediaItemDict, SortKey, SortOrder

_logger = logging.getLogger(__name__)


def list_albums(config: Config) -> list[str]:
    """List all album IDs (root folder names)."""
    return source.list_albums(config.source_dir)


def get_album_detail(
    config: Config,
    album_id: str,
    sort: SortKey = SortKey.DATE,
    order: SortOrder = SortOrder.ASC,
) -> Optional[dict[str, object]]:
    """Get album metadata with sorted items."""
    album_path = config.source_dir / album_id
    if not album_path.exists():
        return None

    # Load index (may be None if not extracted).
    index_path = data.album_index_path(config.data_dir, album_id)
    items = data.load_index(index_path) or []

    # Sort items.
    sorted_items = _sort_items(items, sort, order)

    # Count and cover.
    count = len(items)
    cover = _cover_hash(items, data.load_cover(index_path))

    return {
        "id": album_id,
        "count": count,
        "cover": _cover_url(album_id, cover),
        "cover_hash": cover,
        "items": sorted_items,
    }


def get_album_list_with_status(
    config: Config,
    extraction_status_fn: Callable[[str], dict[str, object]],
) -> list[AlbumListItemDict]:
    """List albums with counts and covers."""
    albums = list_albums(config)
    result: list[AlbumListItemDict] = []

    for album_id in albums:
        album_path = config.source_dir / album_id

        # Load index.
        index_path = data.album_index_path(config.data_dir, album_id)
        items = data.load_index(index_path) or []

        cover = _cover_hash(items, data.load_cover(index_path))

        # Get extraction status.
        status_dict = extraction_status_fn(album_id)
        status_str = str(status_dict.get("status", "idle"))

        item: AlbumListItemDict = {
            "id": album_id,
            "count": len(items),
            "cover": _cover_url(album_id, cover),
            "cover_hash": cover,
            "status": status_str,
        }
        result.append(item)

    return result


def _sort_items(
    items: list[MediaItemDict],
    sort: SortKey,
    order: SortOrder,
) -> list[MediaItemDict]:
    """Sort media items by key and order."""
    reverse = order == SortOrder.DESC

    if sort == SortKey.DATE:
        return _sort_by_date(items, order)

    if sort == SortKey.NAME:
        return sorted(
            items,
            key=lambda x: x.get("path", ""),
            reverse=reverse,
        )

    return items


def _sort_by_date(
    items: list[MediaItemDict], order: SortOrder
) -> list[MediaItemDict]:
    """Dated items by date; undated always after, by name.

    Example (desc): [2024, 2010, <none a.jpg>, <none b.jpg>]
    """
    dated = [i for i in items if i.get("date") is not None]
    undated = [i for i in items if i.get("date") is None]

    dated.sort(key=lambda x: x.get("date") or 0, reverse=order == SortOrder.DESC)
    undated.sort(key=lambda x: x.get("path", ""))

    return dated + undated


def set_cover(config: Config, album_id: str, media_hash: str) -> bool:
    """Store chosen cover in index. False if album not extracted or hash unknown."""
    index_path = data.album_index_path(config.data_dir, album_id)
    items = data.load_index(index_path) or []

    if not any(item.get("hash") == media_hash for item in items):
        return False

    return data.save_cover(index_path, media_hash)


def _cover_hash(items: list[MediaItemDict], chosen: Optional[str]) -> Optional[str]:
    """Cover item: user choice (if still present) > cover.jpg > first item."""
    hashes = {item["hash"] for item in items}
    if chosen in hashes:
        return chosen

    cover_item = next(
        (item for item in items if Path(item["path"]).name == "cover.jpg"),
        None,
    )
    if cover_item:
        return cover_item["hash"]

    if items:
        return items[0]["hash"]

    return None


def _cover_url(album_id: str, cover: Optional[str]) -> Optional[str]:
    if not cover:
        return None
    return f"/api/albums/{album_id}/media/{cover}/thumb"
