# Moments

Self-hosted photo album. Reads folder hierarchies, extracts metadata (EXIF, GPS, video info), and serves a minimal web UI.

## Development

### Prerequisites
- Python 3.11+
- ffmpeg (for video metadata and poster extraction)

### Setup
```bash
# Create virtual environment.
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in dev mode.
pip install -e ".[dev]"

# Copy config template.
cp config.example.json config.json

# Edit config.json with your album paths.
# Set source_dir to a folder containing album subfolders.
# Set data_dir to where extracted metadata will be stored.
```

### Run
```bash
# Start server (default port 8000).
python -m moments

# Visit http://localhost:8000
```

### Test
```bash
# Run all tests.
pytest

# Run with coverage.
pytest --cov=moments

# Type check (mypy).
mypy --strict src tests
```

## Production

### Docker
```bash
# Build image.
docker compose build

# Run.
docker compose up -d

# Logs.
docker compose logs -f
```

### Configuration
Edit `config.json`:
- `port`: HTTP server port (default 8000).
- `source_dir`: Path to album folders (required; folders inside this directory are albums).
- `data_dir`: Path for extracted metadata, thumbnails, previews.
- `thumb_size`: Thumbnail max dimension in pixels (default 200).
- `preview_size`: Preview max dimension in pixels (default 800).

### Security
- **No authentication**: app is for trusted networks only.
- **Read-only source**: source folder is mounted read-only.
- **Path validation**: all file serving is validated to prevent path traversal.

### Volume Mounts
- `source_dir`: mount as read-only (`:ro`).
- `data_dir`: mount as named volume for persistence.
- `config.json`: mount into container.

### Troubleshooting
- If videos don't show metadata: ffmpeg may not be in PATH inside container.
- If HEIC images don't convert: pillow-heif plugin not loaded.
- Check logs: `docker compose logs`.

## Architecture

See [docs/global_spec.md](docs/global_spec.md) for detailed specification.

### Layers
- **Routes** (`src/moments/routes/`): FastAPI endpoints.
- **Services** (`src/moments/services/`): business logic (albums, extraction).
- **Storage** (`src/moments/storage/`): metadata index, file scanning.
- **Drivers** (`src/moments/drivers/`): media processing (EXIF, video info).

### Extraction
- Triggered: on first album view or manual re-extract button.
- Runs in background (non-blocking).
- Incremental: skips unchanged files (path + mtime + size).
- Failure-tolerant: bad files logged and skipped.
