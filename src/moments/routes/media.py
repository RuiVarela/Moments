"""Media file serving (original, thumb, preview)."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from moments.storage import data

router = APIRouter(prefix="/api/albums/{album_id}/media/{media_hash}", tags=["media"])


@router.get("/original")
def get_original(
    album_id: str, media_hash: str, request: Request
) -> FileResponse:
    """Serve original media file (image or video)."""
    config = request.app.state.config

    # Load index to find the file.
    index_path = data.album_index_path(config.data_dir, album_id)
    items = data.load_index(index_path)

    if not items:
        raise HTTPException(status_code=404, detail="Album not extracted")

    item = next(
        (i for i in items if i.get("hash") == media_hash), None
    )
    if not item:
        raise HTTPException(status_code=404, detail="Media not found")

    # Resolve file path and validate it's inside source_dir.
    file_path = config.source_dir / album_id / Path(item["path"])
    try:
        file_path = file_path.resolve()
        album_path = (config.source_dir / album_id).resolve()
        if not str(file_path).startswith(str(album_path)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="image/jpeg"
        if item["type"] == "image"
        else "video/mp4",
    )


@router.get("/thumb")
def get_thumb(
    album_id: str, media_hash: str, request: Request
) -> FileResponse:
    """Serve thumbnail (200px)."""
    config = request.app.state.config

    thumb = data.thumb_path(config.data_dir, album_id, media_hash)
    if not thumb.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(thumb, media_type="image/jpeg")


@router.get("/preview")
def get_preview(
    album_id: str, media_hash: str, request: Request
) -> FileResponse:
    """Serve preview (800px)."""
    config = request.app.state.config

    preview = data.preview_path(config.data_dir, album_id, media_hash)
    if not preview.exists():
        raise HTTPException(status_code=404, detail="Preview not found")

    return FileResponse(preview, media_type="image/jpeg")
