from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration loaded from JSON and env vars."""

    port: int = Field(default=8000, description="HTTP server port")
    source_dir: Path = Field(description="Path to album folders")
    data_dir: Path = Field(description="Path for extracted metadata")
    thumb_size: int = Field(default=200, description="Thumbnail max dimension (px)")
    preview_size: int = Field(default=800, description="Preview max dimension (px)")

    class Settings:
        env_file = "config.json"
        env_file_encoding = "utf-8"

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
