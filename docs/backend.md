# Backend Implementation

FastAPI-based photo album backend with background extraction jobs, strict typing, and layered architecture.

## Project Structure

```
src/moments/
├── __init__.py              # Package marker
├── __main__.py              # Entry point; loads config, runs uvicorn
├── app.py                   # FastAPI factory; creates app + registers routers
├── config.py                # Pydantic config; loads from config.json, validates source_dir exists
├── types.py                 # Enums (MediaType, ExtractionStatus, SortKey), TypedDicts
├── py.typed                 # Marker for mypy
│
├── drivers/                 # Low-level media processing
│   ├── images.py            # Pillow: EXIF (date, GPS), resize to thumb/preview
│   └── videos.py            # ffprobe (metadata), ffmpeg (poster extraction)
│
├── storage/                 # Metadata persistence and scanning
│   ├── source.py            # Walk album recursively; skip hidden, symlinks, root files
│   └── data.py              # Index JSON (atomic write); file hashing; thumb/preview paths
│
├── services/                # Business logic
│   ├── albums.py            # List albums, get detail, sort by date/mtime/name, cover selection
│   └── extraction.py        # ExtractionManager: per-album background jobs, state tracking
│
└── routes/                  # HTTP endpoints
    ├── albums.py            # GET /api/albums, GET /api/albums/{id}
    ├── media.py             # GET thumb/preview/original (FileResponse with path validation)
    └── extract.py           # POST /api/albums/{id}/extract, GET status
```

## Layering (Per AGENTS.md)

Strictly enforced: routes → services → storage → drivers. No cross-layer shortcuts.

- **Routes**: Accept HTTP requests, call service layer only.
- **Services**: Business logic (albums, extraction jobs); call storage/drivers.
- **Storage**: Index persistence, file scanning, path resolution.
- **Drivers**: Raw media processing (EXIF, resizing, ffmpeg calls).

## Typing

Full strict typing throughout:
- All function/method params and returns have type hints.
- `TypedDict` for JSON payloads (e.g., `MediaItemDict`, `AlbumIndexDict`).
- `StrEnum` for statuses, sort keys, media types (no magic strings).
- Pydantic models for config validation.
- `py.typed` marker; mypy --strict passes.
- No bare `dict`, `Any`, or untyped calls.

## Config (config.py)

Loads from `config.json` (or `$MOMENTS_CONFIG` env var). Validates at startup:

```python
port: int                  # HTTP server port
source_dir: Path           # Album root (must exist, is directory)
data_dir: Path             # Extracted metadata storage
thumb_size: int = 200      # Thumbnail max dimension
preview_size: int = 800    # Preview max dimension
```

Fails fast: missing `source_dir` raises `ValueError` on startup.

## Album Structure

**Albums**: root-level folders under `source_dir`.
- Album ID = folder name (validated: no `/`, `..`, hidden).
- All nested subfolders (any depth) are part of same album (flattened).

**Ignored** in scan:
- Hidden files/folders (prefix `.`).
- Symlinks.
- Loose files at album root (depth 0).

Example:
```
source_dir/
├── vacation/              # Album: id="vacation"
│   ├── cover.jpg         # File at root (ignored)
│   ├── 2024-01/          # Subfolder (flattened into vacation)
│   │   ├── photo_001.jpg
│   │   └── photo_002.jpg
│   └── 2024-02/
│       ├── trip.mp4
│       └── sunset.jpg
└── beach/                # Album: id="beach"
    └── day1/
        └── swim.jpg
```

## Extraction (services/extraction.py)

### Flow
1. **Scan** (source.py): walk album, collect files by type (image/video).
2. **Check incremental**: compare to index; reuse unchanged items.
3. **Extract metadata**: EXIF date/GPS, video duration/codec/creation date.
4. **Create thumbnails**: resize to thumb_size and preview_size.
5. **Save index**: atomic write (tmp + rename).

### Incremental Logic
Reuse index entry if:
- `path + mtime + size` match existing item.
- Thumb/preview files exist.

Skips unchanged files to avoid re-processing.

### States
- `idle`: Not running, index exists or not started.
- `running`: Job in progress.
- `failed`: Job errored; `error` field has message.

### Triggers
- **On album entry**: `GET /api/albums/{id}` starts extraction if no index and not running.
- **Manual**: `POST /api/albums/{id}/extract` (re-extract button).

Extraction runs in background (thread pool, single worker); does not block API.

### Error Handling
Per-file errors logged and skipped; run continues. If all files fail, state = `failed`.

## Index Format (data.py)

### File: `data_dir/<album>/index.json`

```json
{
  "version": 1,
  "items": [
    {
      "hash": "abc123def456...",
      "path": "2024-01/photo_001.jpg",
      "type": "image",
      "mtime": 1705000000,
      "size": 51234,
      "date": 1705000000,
      "gps": {"lat": 37.7749, "lon": -122.4194},
      "width": 800,
      "height": 600,
      "duration": null,
      "codec": null
    }
  ]
}
```

**Atomic write**: write to temp file, rename to target (no partial/corrupted files).

**Media hash**: `sha1(relative_path)[:16]` (stable across runs, used in URLs).

## Drivers

### Images (drivers/images.py)
- **EXIF parsing**: datetime, GPS (lat/lon from IFD), dimensions.
- **Fallback date**: EXIF DateTimeOriginal → DateTime → mtime.
- **Resize**: Pillow thumbnail to max_size (LANCZOS), save as JPEG.
- **Error handling**: bad EXIF logged, still create thumbnails.

### Videos (drivers/videos.py)
- **ffprobe**: extract creation_time, duration, codec, width/height.
- **Poster**: ffmpeg "select keyframe" or fallback to 1-second frame.
- **Skip if ffmpeg missing**: logs debug message, returns empty metadata.
- **Error tolerance**: failed ffmpeg → no poster, but video still indexed.

## API Endpoints

### Albums
- `GET /api/albums`: List all with counts, covers, extraction status.
- `GET /api/albums/{id}?sort=date|mtime|name&order=asc|desc`: Detail + sorted items.
  - Starts extraction if not done.
  - Returns extraction status.

### Media
- `GET /api/albums/{id}/media/{hash}/original`: Original file (image/video).
  - Serves from source_dir; validates path is inside album.
  - Returns 404 if file missing.
- `GET .../thumb`: 200px thumbnail from data_dir.
- `GET .../preview`: 800px preview from data_dir.

All file serving uses `FileResponse` (range support for video seeking).

### Extraction
- `POST /api/albums/{id}/extract`: Start job; returns `{"status": "started"}`.
- `GET /api/albums/{id}/extract/status`: Job status (idle/running/failed + progress).

## Testing

### Fixtures (tests/conftest.py)
- `tmp_albums_dir`, `tmp_data_dir`: temporary directories.
- `config`: Config pointing to temp dirs.
- `album_with_images`: test album with 3 JPEG files + cover.jpg.
- `album_empty`: empty album (no files).
- `create_test_album()`: helper to build albums with nested folders.
- `create_test_video()`: ffmpeg-generated video (skipped if ffmpeg absent).

### Storage Tests (tests/test_storage.py)
- Album listing (skip hidden).
- Scan rules (root files ignored, nested included).
- Index save/load.
- Atomic write (tmp + rename).

### API Tests (tests/test_api.py)
- List albums (empty, with data).
- Get album detail (triggers extraction).
- Sorting (date/mtime/name, asc/desc).
- Extraction status.
- File serving (404 before extraction).
- Path traversal protection.

Run: `pytest` (all tests) or `pytest -k test_name` (specific).

## Dependencies

### Runtime
- `fastapi>=0.104.0`: Web framework.
- `uvicorn>=0.24.0`: ASGI server.
- `pillow>=10.0.0`: Image processing (EXIF, resize).
- `pillow-heif>=0.15.0`: HEIC support.
- `pydantic>=2.5.0`: Config validation.

### Dev
- `pytest>=7.4.0`: Test runner.
- `httpx>=0.25.0`: Test client.
- `mypy>=1.7.0`: Type checking (strict).

### System
- `ffmpeg`: Video metadata and poster extraction (optional but recommended).

## Constants & Enums

### types.py
```python
class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"

class ExtractionStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"

class SortKey(StrEnum):
    DATE = "date"
    MTIME = "mtime"
    NAME = "name"

class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"
```

### storage/source.py
```python
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov"}
```

### storage/data.py
```python
_INDEX_VERSION = 1  # Bump if index schema changes.
```

## Security

- **Path validation**: all file serving checks resolved path is inside album/data folders.
- **No auth**: trusted network only.
- **Read-only source**: mount read-only in Docker.
- **Config validation**: fails if source_dir doesn't exist.
