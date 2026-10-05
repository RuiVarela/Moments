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

**Ignored**: loose files directly in `source_dir` (belong to no album), hidden files/folders (prefix `.`), symlinks. Files directly in an album folder are part of the album.

## Media
**Image formats**: JPEG, PNG, WebP, HEIC, GIF (Assumption).

**Video formats**: MP4, WebM, MOV, AVI. No transcoding; browser handles playback natively (AVI usually won't play in browsers; served as-is).

**Date**: EXIF date-taken (images) or creation date (videos); fallback: file name `YYYY-MM-DD_*.ext` (e.g. `2006-03-03_00001.jpg`). Otherwise undated.

**Ordering**: by date (undated last, by name) or by name.

## Extraction
Per-album metadata job:
- **Input**: read-only access to source folder.
- **Output**: `data_dir/<album>/` with index, thumbnails, previews.

**Extracted metadata**:
- Images: EXIF date, GPS coords, dimensions.
- Videos: creation date, duration, dimensions, codec; poster frame (first keyframe or 1s mark).

**Re-extract**: reprocesses every file.

**Output layout**:
```
data_dir/<album>/index.json              # metadata + file list
data_dir/<album>/thumbs/<hash>.jpg       # 200px (image or video poster)
data_dir/<album>/previews/<hash>.jpg     # 800px (image or video poster)
```

**Triggers**:
- **On album entry**: if not extracted, start automatically (background; does not block UI).
- **Manual**: POST `/api/albums/<id>/extract` endpoint (re-extract button on frontend).

Extraction runs in background; does not block API or UI. Progress tracked via status endpoint.

**Failure handling**: bad file logged, skipped; run continues. States: `idle` / `running` / `failed`.

## API

### Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/albums` | GET | List all albums with counts, covers, extraction status. |
| `/api/albums/<id>` | GET | Album metadata + media array. Query params: `sort` (date\|name), `order` (asc\|desc). |
| `/api/albums/<id>/media/<hash>/thumb` | GET | Thumbnail (image or video poster). |
| `/api/albums/<id>/media/<hash>/preview` | GET | Preview (image or video poster). |
| `/api/albums/<id>/media/<hash>/original` | GET | Original file (image or video). |
| `/api/albums/<id>/extract` | POST | Start extraction job. |
| `/api/albums/<id>/extract/status` | GET | Extraction status (state, done/total, error if failed). |

### Query Parameters
- **sort**: `date` (default; undated last), `name` — sorting key for media items.
- **order**: `asc` (default), `desc` — sort direction.

## Frontend
Three-page flow:

**1. Landing page**: grid of all albums with cover image. Cover selection: prefer `cover.jpg` in album root; fallback to first sorted media.

**2. Album view**: full-size grid of media (images + videos) with lazy-loaded thumbnails.
- **Sorting**: dropdown to choose date taken or filename (default: date taken) + asc/desc toggle.
- **By date**: grid split by month with a month/year header (e.g. "March 2006"); undated items last under "Undated".
- **Options button** (top-right): re-extract album, re-extract all albums (one after the other), show extraction status.
- Auto-starts extraction if not yet done (user sees status in options).

**3. Gallery/viewer**: single full-screen media display (image or video player).
- **Navigation**: 
  - Left/Right arrow keys (desktop).
  - Swipe left/right (mobile).
  - Previous/Next buttons.
  - Close button (ESC key or X button).
- **Media source**:
  - Images: original file (JPEG/PNG/WebP/GIF).
  - HEIC/HEIF: preview (800px, since browsers don't render HEIC).
  - Videos: original file; browser plays natively.
- **Info overlay** (toggle via `i` key): show date, dimensions, GPS as OpenStreetMap link labelled with place name (browser → Nominatim reverse geocoding; no embedded map).

No build step; vanilla JS + CSS Grid.

## Open Questions
(None for MVP.)
