# Moments

Family photo gallery.
Very simple list of albums. Intended to run on a low spec self hosted machine.
Reads folder hierarchies, extracts metadata (EXIF, GPS, video info), and serves a minimal web UI.

This was developed using AI.

## Development

### Prerequisites
- Python 3.12+
- ffmpeg (for video metadata and poster extraction)
- Google Chrome (Playwright browser checks use it via `channel="chrome"`; or run `playwright install chromium`) - for AI testing

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

# Visit http://localhost:8000 (UI) or http://localhost:8000/api/albums (API)
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

### Docker run
```bash
docker run -d --name moments -p 8000:8000 \
  -v /path/to/albums:/source:ro \
  -v moments_data:/data \
  -e PUID=$(id -u) -e PGID=$(id -g) \
  ruifilipevarela/moments:latest
```
Open http://localhost:8000. Images: `linux/amd64`, `linux/arm64`.

### Docker Compose
```bash
SOURCE_DIR=/path/to/albums docker compose up -d
docker compose logs -f
```

### Container layout
| Path / env | Purpose |
|---|---|
| `/source` | Albums; mount read-only (`:ro`). Each subfolder = album. |
| `/data` | Index, thumbnails, previews. Volume or host dir. |
| `/app/config.json` | Built-in defaults; mount your own to override. |
| `PUID` / `PGID` | Host user/group owning `/data` files (default 1000). |

### Configuration
Defaults are baked into the image. To override, mount a `config.json` at `/app/config.json` (keep `source_dir: /source`, `data_dir: /data`):
- `port`: HTTP server port (default 8000).
- `source_dir`: Path to album folders (required; folders inside this directory are albums).
- `data_dir`: Path for extracted metadata, thumbnails, previews.
- `thumb_size`: Thumbnail square side in pixels (default 200).
- `preview_size`: Preview square side in pixels (default 800).
- `jpeg_quality`: Thumbnail/preview JPEG quality, 1..95 (default 60).
- `num_threads`: Files extracted in parallel (default: number of CPU cores).

### Security
- **No authentication**: app is for trusted networks only.
- **Read-only source**: source folder is mounted read-only.
- **Path validation**: all file serving is validated to prevent path traversal.

### Troubleshooting
- `/data` permission errors: set `PUID`/`PGID` to the owner of the host data dir.
- Check logs: `docker compose logs` / `docker logs moments`.

## Publishing (Docker Hub)

### 1. Push (multi-arch)
```bash

docker login
docker buildx create --name moments-builder --use     # once

VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)
echo "Version: ${VERSION}"

docker buildx build --platform linux/amd64,linux/arm64 \
  --build-arg VERSION=${VERSION} \
  -t ruifilipevarela/moments:${VERSION} -t ruifilipevarela/moments:latest \
  --push .
```

### 2 clean Verify
```bash
docker buildx imagetools inspect ruifilipevarela/moments:latest   # lists amd64 + arm64
```

## Documentation
- [docs/global_spec.md](docs/global_spec.md): Feature specification (user-facing).
- [docs/backend.md](docs/backend.md): Backend implementation details (developer guide).
- [docs/frontend.md](docs/frontend.md): Frontend implementation details (developer guide).
