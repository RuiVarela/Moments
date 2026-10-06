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
│   ├── source.py            # Walk album recursively; skip hidden, symlinks
│   └── data.py              # Index JSON (atomic write); file hashing; thumb/preview paths
│
├── services/                # Business logic
│   ├── albums.py            # List albums, get detail, sort by date/name, cover selection
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

## Configuration (config.py)

Loads from `config.json` file (or `$MOMENTS_CONFIG` env var). Validates at startup.

### File: `config.json`

**Required**:
- `port` (int): HTTP server port (default 8000).
- `source_dir` (string): path to album folders root (validated: must exist, must be directory).
- `data_dir` (string): path for extracted metadata, thumbnails, previews.

**Optional**:
- `thumb_size` (int): thumbnail square side in pixels (default 200).
- `preview_size` (int): preview square side in pixels (default 800).
- `jpeg_quality` (int): thumb/preview JPEG quality, 1..95 (default 60).
- `num_threads` (int): files extracted in parallel (default: CPU cores; must be ≥ 1).

### Example

```json
{
  "port": 8000,
  "source_dir": "/mnt/albums",
  "data_dir": "/app/data",
  "thumb_size": 200,
  "preview_size": 800,
  "jpeg_quality": 60,
  "num_threads": 4
}
```

### Validation

- **Fail-fast**: missing or invalid `source_dir` raises `ValueError` at startup.
- **Type coercion**: string paths converted to `Path` objects.
- **Positive sizes**: `thumb_size` and `preview_size` must be > 0.
- **JPEG quality**: `jpeg_quality` must be 1..95.

Pydantic validates config against schema on load (see config.py for validators).

## Album Structure

**Albums**: root-level folders under `source_dir`.
- Album ID = folder name (validated: no `/`, `..`, hidden).
- All nested subfolders (any depth) are part of same album (flattened).

**Ignored** in scan:
- Hidden files/folders (prefix `.`).
- Symlinks.
- Loose files directly in `source_dir` (not inside any album).

Files directly in an album folder are included (flat albums, `cover.jpg`).

Example:
```
source_dir/
├── vacation/              # Album: id="vacation"
│   ├── cover.jpg         # Album root file (included; used as cover)
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
2. **Per file, in parallel** (`_process_file`, `num_threads` workers):
   metadata (EXIF / ffprobe, filename date fallback) + thumb/preview.
3. **Save index**: items sorted by path; atomic write (tmp + rename).

```
scan ─► files ─┬─► worker 1 ─┐
               ├─► worker 2 ─┼─► as_completed ─► done++ ─► sort ─► index.json
               └─► worker N ─┘   (job thread only)
```

Threads, not processes: Pillow decode/resize and ffmpeg release the GIL.
Measured: 889-file album 54.3 s (1 thread) → 8.2 s (10 threads, 8 perf cores).

### States
- `idle`: Not running, index exists or not started.
- `running`: Job in progress.
- `failed`: Job errored; `error` field has message.

### Triggers
- **On album entry**: `GET /api/albums/{id}` starts extraction if no index and not running.
- **Manual**: `POST /api/albums/{id}/extract` (re-extract button).

Extraction runs in background: one album at a time (manager executor, single worker), files within it on `num_threads` workers; does not block API.

### Error Handling
Per-file errors logged and skipped; run continues and still counts toward `done`. State = `failed` only on album-level errors (folder missing, scan/index failure).

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
      "size": 51234,
      "date": 1705000000,
      "gps": {"lat": 37.7749, "lon": -122.4194},
      "width": 800,
      "height": 600,
      "duration": null,
      "codec": null
    }
  ],
  "cover": "abc123def456..."
}
```

`cover` (optional): user-chosen cover item hash. Kept across re-extraction. Cover = `cover` if still in items > `cover.jpg` > first item.

**Atomic write**: write to temp file, rename to target (no partial/corrupted files).

**Media hash**: `sha1(relative_path)[:16]` (stable across runs, used in URLs).

## Drivers

### Images (drivers/images.py)
- **EXIF parsing**: datetime, GPS (lat/lon from IFD), dimensions.
- **Fallback date**: EXIF DateTimeOriginal → DateTime → file name `YYYY-MM-DD_*.ext` (drivers/filenames.py) → none.
- **Renditions** (`create_renditions`): one decode → preview + thumb, center-cropped squares.
  ```
  4000x3000 JPEG ─draft─► 1000x750 ─crop+resize─► 800x800 ─rotate─► preview.jpg
                                                     └─resize─► 200x200 ─► thumb.jpg
  ```
  - Square side = min(shorter source side, target); never upscaled.
  - `draft()`: JPEG decoded at 1/2–1/8 scale, shorter side still ≥ target (biggest win).
  - Largest first; each smaller size resized from the previous.
  - EXIF orientation applied after first resize (fewer pixels); outputs upright.
  - ~2.4× faster than decoding per size (57 → 24 ms/photo, 3.7 MP avg).
- **Dimensions**: width/height reported as displayed (orientation-aware).
- **Error handling**: bad EXIF logged, still create thumbnails.

### Videos (drivers/videos.py)
- **ffprobe**: extract creation_time, duration, codec, width/height.
- **Poster**: ffmpeg "select keyframe" or fallback to 1-second frame. Center-cropped square, never upscaled. Run once at preview size; thumb resized from it via `create_renditions`.
- **Skip if ffmpeg missing**: logs debug message, returns empty metadata.
- **Error tolerance**: failed ffmpeg → no poster, but video still indexed.

## API Endpoints

### Albums
- `GET /api/albums`: List all with counts, covers (`cover` thumb URL + `cover_hash`), extraction status.
- `PUT /api/albums/{id}/cover` body `{"hash": "..."}`: set cover. 404 if album not extracted or hash unknown.
- `GET /api/albums/{id}?sort=date|name&order=asc|desc`: Detail + sorted items.
  - Starts extraction if not done.
  - Returns extraction status.

### Media
- `GET /api/albums/{id}/media/{hash}/original`: Original file (image/video).
  - Serves from source_dir; validates path is inside album.
  - Returns 404 if file missing.
- `GET .../thumb`: 200px thumbnail from data_dir.
- `GET .../preview`: 800px preview from data_dir.

All file serving uses `FileResponse`: `Accept-Ranges: bytes`, `Range` → 206 partial, past end → 416 (video seeking). Covered by tests/test_static.py.

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
- Scan rules (album root + nested included; source_dir loose files ignored).
- Index save/load.
- Atomic write (tmp + rename).

### API Tests (tests/test_api.py)
- List albums (empty, with data).
- Get album detail (triggers extraction).
- Sorting (date/name, asc/desc; undated last).
- Extraction status.
- File serving (404 before extraction).
- Path traversal protection.

Run: `pytest` (all tests) or `pytest -k test_name` (specific).

## Dependencies

### Runtime
- `fastapi>=0.104.0`: Web framework.
- `starlette>=0.39.0`: pinned for `FileResponse` HTTP Range (206/416); needed for video seeking and Safari playback.
- `uvicorn>=0.24.0`: ASGI server.
- `pillow>=10.0.0`: Image processing (EXIF, resize).
- `pillow-heif>=0.15.0`: HEIC support.
- `pydantic>=2.5.0`: Config validation.

### Dev
- `pytest>=7.4.0`: Test runner.
- `httpx2>=2.13.0`: Test client backend (Starlette warns with plain `httpx`).
- `playwright>=1.40.0`: Browser layout checks (installed Chrome).
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
    NAME = "name"

class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"
```

### storage/source.py
```python
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi"}
```

### storage/data.py
```python
_INDEX_VERSION = 1  # Bump if index schema changes.
```

## Deployment

### Image (`Dockerfile`)

```
python:3.14-slim + ffmpeg
  pip install .          (non-editable; code + static/ in site-packages)
  /app/config.json       (docker/config.json: source_dir=/source, data_dir=/data)
  ENTRYPOINT entrypoint.sh ─► chown /data (top-level) ─► setpriv PUID:PGID ─► python -m moments
```

- **Packaging**: `pyproject.toml` uses `packages.find` + `package-data` (`static/**`, `py.typed`); `tests/test_packaging.py` builds the wheel and checks contents.
- **User**: root only in entrypoint; app runs as `PUID:PGID` (default 1000) via `setpriv` (util-linux, already in slim).
- **Healthcheck**: python `urllib` → `/api/albums` (no curl in slim).
- **Volumes**: `/data` declared; `/source` expected read-only.
- **Context**: `.dockerignore` excludes venv, .git, working_folder (photos), tests, docs.

### Compose (`docker-compose.yml`)

- `image: ruifilipevarela/moments:latest` + `build: .`
- `${SOURCE_DIR}:/source:ro` (required; compose errors if unset), `moments_data:/data`
- `PUID`/`PGID` env; optional `./config.json:/app/config.json:ro`

### Environment Variables

- `MOMENTS_CONFIG`: config path (image: `/app/config.json`; dev: `config.json` in cwd).
- `PUID` / `PGID`: owner of files written to `/data`.
- `SOURCE_DIR`: compose only; host albums folder.

## Security

- **Path validation**: all file serving checks resolved path is inside album/data folders.
- **No auth**: trusted network only (no authentication or authorization).
- **Read-only source**: source folder mounted `:ro` (read-only) in container.
- **Config validation**: fails fast if `source_dir` doesn't exist.
- **Atomic writes**: index.json written atomically (tmp + rename) to prevent corruption.
