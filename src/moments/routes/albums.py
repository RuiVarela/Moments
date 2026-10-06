"""Album list and detail endpoints."""
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from moments.services import albums
from moments.types import AlbumListItemDict, SortKey, SortOrder

router = APIRouter(prefix="/api/albums", tags=["albums"])


class CoverBody(BaseModel):
    """PUT /cover body: {"hash": "<media hash>"}."""

    hash: str


@router.get("")
def list_albums(request: Request) -> list[AlbumListItemDict]:
    """List all albums with counts, covers, and extraction status."""
    config = request.app.state.config
    extraction_mgr = request.app.state.extraction_manager

    return albums.get_album_list_with_status(
        config, extraction_mgr.get_status
    )


@router.get("/{album_id}")
def get_album(
    album_id: str,
    request: Request,
    sort: str = "date",
    order: str = "asc",
) -> dict[str, Any]:
    """Get album detail with sorted media items.

    Query params:
    - sort: date (default), name
    - order: asc (default), desc
    """
    config = request.app.state.config
    extraction_mgr = request.app.state.extraction_manager

    # Start extraction if not done.
    extraction_mgr.start_if_needed(album_id)

    # Validate sort/order.
    try:
        sort_key = SortKey(sort)
        sort_order = SortOrder(order)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort or order: {sort}, {order}",
        )

    # Get album detail.
    detail = albums.get_album_detail(
        config, album_id, sort_key, sort_order
    )

    if detail is None:
        raise HTTPException(status_code=404, detail="Album not found")

    # Add extraction status.
    detail["status"] = extraction_mgr.get_status(album_id)

    return detail


@router.put("/{album_id}/cover")
def put_cover(album_id: str, body: CoverBody, request: Request) -> dict[str, str]:
    """Set album cover to one of its media items."""
    config = request.app.state.config

    if not albums.set_cover(config, album_id, body.hash):
        raise HTTPException(status_code=404, detail="Album or media not found")

    return {"cover_hash": body.hash}
