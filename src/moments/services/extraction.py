"""Extraction job manager: per-album background jobs."""
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Optional

from moments.config import Config
from moments.drivers import images, videos
from moments.storage import data, source
from moments.types import ExtractionStatus, MediaItemDict

_logger = logging.getLogger(__name__)


class _JobState:
    """In-memory state for an extraction job."""

    __slots__ = ("status", "done", "total", "error")

    def __init__(self) -> None:
        self.status = ExtractionStatus.IDLE
        self.done = 0
        self.total = 0
        self.error: Optional[str] = None


class ExtractionManager:
    """Manages per-album extraction jobs, runs in background."""

    def __init__(self, config: Config, max_workers: int = 1) -> None:
        self._config = config
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: dict[str, _JobState] = {}
        self._lock = Lock()

    def get_status(self, album_id: str) -> dict[str, object]:
        """Get status of an extraction job."""
        with self._lock:
            job = self._jobs.get(album_id)

        if not job:
            # Job not started yet or completed; check if index exists.
            index_path = data.album_index_path(self._config.data_dir, album_id)
            if index_path.exists():
                return {
                    "status": ExtractionStatus.IDLE,
                    "done": 0,
                    "total": 0,
                    "error": None,
                }
            return {
                "status": ExtractionStatus.IDLE,
                "done": 0,
                "total": 0,
                "error": None,
            }

        return {
            "status": job.status,
            "done": job.done,
            "total": job.total,
            "error": job.error,
        }

    def start_if_needed(self, album_id: str) -> None:
        """Start extraction if not already extracted and not running."""
        with self._lock:
            job = self._jobs.get(album_id)
            if job and job.status == ExtractionStatus.RUNNING:
                return  # Already running.

        # Check if index exists.
        index_path = data.album_index_path(self._config.data_dir, album_id)
        if index_path.exists():
            return  # Already extracted.

        # Start extraction.
        self.start(album_id)

    def start(self, album_id: str) -> None:
        """Manually start (re-)extraction."""
        with self._lock:
            # If already running, no-op.
            job = self._jobs.get(album_id)
            if job and job.status == ExtractionStatus.RUNNING:
                return

            # Create new job state.
            job = _JobState()
            job.status = ExtractionStatus.RUNNING
            self._jobs[album_id] = job

        # Submit to executor.
        self._executor.submit(self._run_extraction, album_id)

    def _run_extraction(self, album_id: str) -> None:
        """Extract album metadata (runs in thread pool)."""
        job: Optional[_JobState]

        with self._lock:
            job = self._jobs.get(album_id)

        if not job:
            return

        try:
            album_path = self._config.source_dir / album_id
            if not album_path.exists():
                job.error = f"Album folder not found: {album_path}"
                job.status = ExtractionStatus.FAILED
                return

            # Scan files.
            scanned = source.scan_album(album_path)
            job.total = len(scanned)

            if not scanned:
                # Empty album: create index with no items.
                self._save_index(album_id, [])
                job.status = ExtractionStatus.IDLE
                return

            # Load existing index for incremental check.
            index_path = data.album_index_path(self._config.data_dir, album_id)
            old_items: list[MediaItemDict] = (
                data.load_index(index_path) or []
            )
            old_index: dict[str, MediaItemDict] = {
                item["hash"]: item for item in old_items
            }

            # Process each file.
            new_items: list[MediaItemDict] = []

            for file_info in scanned:
                rel_path_str: str = file_info["path"]
                item_type: str = file_info["type"]
                rel_path = Path(rel_path_str)
                item_hash = data.media_hash(rel_path)
                full_path = album_path / rel_path

                # Check if file unchanged (incremental).
                stat = full_path.stat()
                old_item = old_index.get(item_hash)

                if old_item and self._is_unchanged(
                    old_item, stat, item_type
                ):
                    new_items.append(old_item)
                    job.done += 1
                    continue

                # Extract metadata and create thumbnails.
                item: MediaItemDict = {
                    "hash": item_hash,
                    "path": str(rel_path),
                    "type": item_type,
                    "mtime": int(stat.st_mtime),
                    "size": stat.st_size,
                    "date": None,
                    "gps": None,
                    "width": None,
                    "height": None,
                    "duration": None,
                    "codec": None,
                }

                if item_type == "image":
                    exif = images.extract_exif(full_path)
                    item.update(exif)
                    images.create_thumbnail(
                        full_path,
                        data.thumb_path(
                            self._config.data_dir, album_id, item_hash
                        ),
                        self._config.thumb_size,
                    )
                    images.create_thumbnail(
                        full_path,
                        data.preview_path(
                            self._config.data_dir, album_id, item_hash
                        ),
                        self._config.preview_size,
                    )
                elif item_type == "video":
                    info = videos.extract_video_info(full_path)
                    item.update(info)
                    videos.create_poster(
                        full_path,
                        data.thumb_path(
                            self._config.data_dir, album_id, item_hash
                        ),
                        self._config.thumb_size,
                    )
                    videos.create_poster(
                        full_path,
                        data.preview_path(
                            self._config.data_dir, album_id, item_hash
                        ),
                        self._config.preview_size,
                    )

                new_items.append(item)
                job.done += 1

            # Save index.
            self._save_index(album_id, new_items)
            job.status = ExtractionStatus.IDLE

        except Exception as e:
            _logger.exception(f"Extraction failed for {album_id}")
            job.error = str(e)
            job.status = ExtractionStatus.FAILED

    def _is_unchanged(
        self,
        item: MediaItemDict,
        stat: object,
        item_type: str,
    ) -> bool:
        """Check if file unchanged compared to index entry."""
        import os

        if not isinstance(stat, os.stat_result):
            return False

        return (
            item.get("mtime") == int(stat.st_mtime)
            and item.get("size") == stat.st_size
            and item.get("type") == item_type
        )

    def _save_index(self, album_id: str, items: list[MediaItemDict]) -> bool:
        """Save index file."""
        index_path = data.album_index_path(self._config.data_dir, album_id)
        return data.save_index(index_path, items)
