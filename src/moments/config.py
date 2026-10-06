import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

_CONFIG_ENV_VAR = "MOMENTS_CONFIG"
_CONFIG_DEFAULT_FILE = "config.json"

# Pillow: above 95 the file grows with no visible gain.
_JPEG_QUALITY_MIN = 1
_JPEG_QUALITY_MAX = 95


class Config(BaseModel):
    """Application configuration."""

    port: int = Field(default=8000, description="HTTP server port")
    source_dir: Path = Field(description="Path to album folders")
    data_dir: Path = Field(description="Path for extracted metadata")
    thumb_size: int = Field(default=200, description="Thumbnail square side (px)")
    preview_size: int = Field(default=800, description="Preview square side (px)")
    jpeg_quality: int = Field(default=60, description="Thumb/preview JPEG quality (1..95)")
    num_threads: int = Field(
        default_factory=lambda: os.cpu_count() or 1,
        description="Files extracted in parallel (default: CPU cores)",
    )

    @field_validator("source_dir", "data_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: object) -> Path:
        """Convert string to Path."""
        if isinstance(v, str):
            return Path(v)
        if isinstance(v, Path):
            return v
        raise ValueError(f"Expected str or Path, got {type(v)}")

    @field_validator("source_dir")
    @classmethod
    def source_dir_exists(cls, v: Path) -> Path:
        """Fail fast if source_dir does not exist."""
        if not v.exists():
            raise ValueError(f"source_dir does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"source_dir is not a directory: {v}")
        return v

    @field_validator("thumb_size", "preview_size")
    @classmethod
    def positive_sizes(cls, v: int) -> int:
        """Sizes must be positive."""
        if v <= 0:
            raise ValueError(f"Size must be positive, got {v}")
        return v

    @field_validator("jpeg_quality")
    @classmethod
    def valid_quality(cls, v: int) -> int:
        """Pillow JPEG quality range."""
        if not _JPEG_QUALITY_MIN <= v <= _JPEG_QUALITY_MAX:
            raise ValueError(
                f"jpeg_quality must be {_JPEG_QUALITY_MIN}..{_JPEG_QUALITY_MAX}, got {v}"
            )
        return v

    @field_validator("num_threads")
    @classmethod
    def positive_threads(cls, v: int) -> int:
        """At least one worker, or nothing is ever extracted."""
        if v < 1:
            raise ValueError(f"num_threads must be >= 1, got {v}")
        return v


def load_config(path: Path | None = None) -> Config:
    """Load configuration from JSON file.

    Args:
        path: explicit config file path. If None, checks $MOMENTS_CONFIG
              env var, then falls back to 'config.json' in cwd.

    Raises:
        FileNotFoundError: config file not found.
        ValueError: invalid config (e.g., source_dir missing).
    """
    if path is None:
        # Check env var, then default.
        env_path = os.environ.get(_CONFIG_ENV_VAR)
        path = Path(env_path) if env_path else Path(_CONFIG_DEFAULT_FILE)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        text = path.read_text()
        data = json.loads(text)
        return Config.model_validate(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
