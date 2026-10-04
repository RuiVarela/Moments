"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from moments.config import Config
from moments.routes import albums, extract, media
from moments.services.extraction import ExtractionManager


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

    # Mount static frontend if it exists.
    static_path = (
        config.source_dir.parent / "static"
        if hasattr(config, "source_dir")
        else None
    )
    if static_path and static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True))

    return app
