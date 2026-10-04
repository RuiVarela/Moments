import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

_CONFIG_ENV_VAR = "MOMENTS_CONFIG"
_CONFIG_DEFAULT_FILE = "config.json"


class Config(BaseModel):
    """Application configuration."""

    port: int = Field(default=8000, description="HTTP server port")
    source_dir: Path = Field(description="Path to album folders")
    data_dir: Path = Field(description="Path for extracted metadata")
    thumb_size: int = Field(default=200, description="Thumbnail max dimension (px)")
    preview_size: int = Field(default=800, description="Preview max dimension (px)")

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
