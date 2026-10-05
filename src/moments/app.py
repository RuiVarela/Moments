"""FastAPI application factory."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from moments.config import Config
from moments.routes import albums, extract, media
from moments.services.extraction import ExtractionManager

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(config: Config) -> FastAPI:
    """Create and configure FastAPI app."""
    app = FastAPI(title="Moments", version="0.1.0")

    # Store config and extraction manager in app state.
    app.state.config = config
    app.state.extraction_manager = ExtractionManager(config)

    # Register routes.
    app.include_router(albums.router)
    app.include_router(media.router)
    app.include_router(extract.router)

    # Mount static frontend (after API routes so /api/* takes priority).
    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True))

    return app
