"""Type definitions for Moments."""
from enum import StrEnum
from typing import Optional, TypedDict


class MediaType(StrEnum):
    """Media type enum."""

    IMAGE = "image"
    VIDEO = "video"


class ExtractionStatus(StrEnum):
    """Extraction job status."""

    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"


class SortKey(StrEnum):
    """Sorting keys for media."""

    DATE = "date"
    NAME = "name"


class SortOrder(StrEnum):
    """Sort order direction."""

    ASC = "asc"
    DESC = "desc"


class MediaItemDict(TypedDict, total=False):
    """Index entry for a media file."""

    hash: str
    path: str
    type: str  # "image" | "video"
    size: int  # Bytes
    date: Optional[int]  # Unix timestamp or None
    gps: Optional[dict[str, float]]  # {"lat": ..., "lon": ...} or None
    width: Optional[int]
    height: Optional[int]
    duration: Optional[float]  # Seconds, for videos
    codec: Optional[str]  # Video codec name


class AlbumIndexDict(TypedDict):
    """Index file structure."""

    version: int
    items: list[MediaItemDict]


class ExtractionProgressDict(TypedDict):
    """Extraction job progress."""

    status: str  # "idle" | "running" | "failed"
    done: int
    total: int
    error: Optional[str]


class AlbumListItemDict(TypedDict, total=False):
    """Album in list response."""

    id: str
    count: int
    cover: Optional[str]  # URL to cover image or None
    status: str
