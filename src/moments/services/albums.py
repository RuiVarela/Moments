"""Album operations: list, detail, sorting, cover selection."""
import logging
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
    cover_url = _get_cover_url(album_id, items) if items else None

    return {
        "id": album_id,
        "count": count,
        "cover": cover_url,
        "items": sorted_items,
    }


def get_album_list_with_status(
    config: Config,
    extraction_status_fn: object,  # Callable[[str], dict]
) -> list[AlbumListItemDict]:
    """List albums with counts and covers."""
    albums = list_albums(config)
    result: list[AlbumListItemDict] = []

    for album_id in albums:
        album_path = config.source_dir / album_id

        # Load index.
        index_path = data.album_index_path(config.data_dir, album_id)
        items = data.load_index(index_path) or []

        cover_url = _get_cover_url(album_id, items) if items else None

        # Get extraction status.
        status_dict = extraction_status_fn(album_id)
        status_str = str(status_dict.get("status", "idle"))

        item: AlbumListItemDict = {
            "id": album_id,
            "count": len(items),
            "cover": cover_url,
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
        return sorted(
            items,
            key=lambda x: x.get("date") or x.get("mtime") or 0,
            reverse=reverse,
        )
    elif sort == SortKey.MTIME:
        return sorted(
            items,
            key=lambda x: x.get("mtime") or 0,
            reverse=reverse,
        )
    elif sort == SortKey.NAME:
        return sorted(
            items,
            key=lambda x: x.get("path", ""),
            reverse=reverse,
        )

    return items


def _get_cover_url(album_id: str, items: list[MediaItemDict]) -> Optional[str]:
    """Get cover URL: prefer cover.jpg item, else first item."""
    # Look for cover.jpg.
    cover_item = next(
        (item for item in items if Path(item["path"]).name == "cover.jpg"),
        None,
    )

    if cover_item:
        return f"/api/albums/{album_id}/media/{cover_item['hash']}/thumb"

    # Fallback to first item.
    if items:
        return f"/api/albums/{items[0]['hash']}/thumb"

    return None
