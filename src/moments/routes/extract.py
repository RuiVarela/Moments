"""Extraction control endpoints."""
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/albums/{album_id}/extract", tags=["extract"])


@router.post("")
def start_extraction(album_id: str, request: Request) -> dict[str, str]:
    """Start (re-)extraction for album."""
    config = request.app.state.config
    extraction_mgr = request.app.state.extraction_manager

    # Validate album exists.
    album_path = config.source_dir / album_id
    if not album_path.exists():
        raise HTTPException(status_code=404, detail="Album not found")

    # Start extraction.
    extraction_mgr.start(album_id)

    return {"status": "started"}


@router.get("/status")
def get_extraction_status(
    album_id: str, request: Request
) -> dict[str, Any]:
    """Get extraction status for album."""
    extraction_mgr = request.app.state.extraction_manager

    return extraction_mgr.get_status(album_id)
