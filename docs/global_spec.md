# Moments — Photo Album Spec

Self-hosted photo album that reads folder hierarchies, extracts metadata, and serves a minimal web UI.

## Goals
- View albums as folders, nested structure flattened per album.
- Display images with dates, thumbnails, and optional GPS map.
- Minimalistic, read-only interface; no auth, no uploads.

## Non-Goals
- User authentication or access control.
- Uploading, editing, or deleting source media.
- Multi-user support or sharing links.

## Albums
Each root-level folder under `source_dir` is one album. All subfolders nest within it (flattened into a single media list).

**Ignored**: loose files at root, hidden files/folders (prefix `.`), symlinks.

## Media
**Image formats**: JPEG, PNG, WebP, HEIC, GIF (Assumption).

**Video formats**: MP4, WebM, MOV (Assumption). No transcoding; browser handles playback natively.

Ordering: by EXIF date-taken (images) or video creation date (metadata), fallback to file modified time (mtime).

## Extraction
Per-album metadata job:
- **Input**: read-only access to source folder.
- **Output**: `data_dir/<album>/` with index, thumbnails, previews.

**Extracted metadata**:
- Images: EXIF date, GPS coords, dimensions.
- Videos: creation date, duration, dimensions, codec; poster frame (first keyframe or 1s mark).

**Incremental**: skip files unchanged (path + mtime + size match).

**Output layout**:
```
data_dir/<album>/index.json              # metadata + file list
data_dir/<album>/thumbs/<hash>.jpg       # 200px (image or video poster)
data_dir/<album>/previews/<hash>.jpg     # 800px (image or video poster)
```

**Triggers**:
- **On album entry**: if not extracted, start automatically (background; does not block UI).
- **Manual**: POST `/api/albums/<id>/extract` endpoint (re-extract button on frontend).

Extraction runs in background; does not block API or UI. UI shows progress

**Failure handling**: bad file logged, skipped; run continues. States: `idle` / `running` / `failed`.

## Architecture
- **Backend**: FastAPI + vanilla JavaScript frontend (no build step, no framework).
- **Dependencies**: FastAPI, uvicorn, Pillow (Assumption).
- **Layers**: routes → services → storage (per AGENTS.md hierarchy).

## API
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/albums` | GET | List all albums with counts. |
| `/api/albums/<id>` | GET | Album metadata + media array. |
| `/api/albums/<id>/media/<hash>/thumb` | GET | Thumbnail (image or video poster). |
| `/api/albums/<id>/media/<hash>/preview` | GET | Preview (image or video poster). |
| `/api/albums/<id>/media/<hash>/original` | GET | Original file (image or video). |
| `/api/albums/<id>/extract` | POST | Start extraction job. |
| `/api/albums/<id>/extract/status` | GET | Extraction status. |

## Frontend
Three-page flow:

**1. Landing page**: grid of all albums with cover image. Cover selection: prefer `cover.jpg` in album root; fallback to first sorted media.

**2. Album view**: full-size grid of media (images + videos) with lazy-loaded thumbnails.
- **Sorting**: dropdown to choose date-taken, file mtime, or filename (default: date-taken).
- **Options button** (top-right): re-extract album, show extraction status.
- Auto-starts extraction if not yet done (user sees status in options).

**3. Gallery/viewer**: single full-screen media display (image or video player).
- **Navigation**: 
  - Left/Right arrow keys (desktop).
  - Swipe left/right (mobile).
  - Previous/Next buttons.
  - Close button (ESC key or X button).
- **Info overlay** (toggle): show date, GPS map if present (optional).

No build step; vanilla JS + CSS Grid.

## Configuration
**File**: `config.json`

**Required**:
- `port` (int): HTTP port; default 8000 (Assumption).
- `source_dir` (string): path to album folders; validated at startup (fail if missing).
- `data_dir` (string): path for extracted metadata and thumbnails.

**Optional**:
- `thumb_size` (int): thumbnail max dimension; default 200px (Assumption).
- `preview_size` (int): preview max dimension; default 800px (Assumption).

**Example**:
```json
{
  "port": 8000,
  "source_dir": "/mnt/albums",
  "data_dir": "/app/data",
  "thumb_size": 200,
  "preview_size": 800
}
```

## Security
- **No authentication**: app is trusted-network-only.
- **Path traversal protection**: all file serving validated against `source_dir` and `data_dir`.
- **Read-only source**: mount source folder read-only in container.

## Deployment
**Docker Compose**:
- Source folder mounted `:ro` (read-only).
- Data folder as named volume (persistent).
- Config file mounted into container.
- Single FastAPI service on mapped port.

## Open Questions
(None for MVP.)
