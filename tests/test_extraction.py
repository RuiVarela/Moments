"""Extraction runs files in parallel, bounded by num_threads."""
import threading
import time
from pathlib import Path

import pytest
from PIL import Image

from moments.config import Config
from moments.drivers import images
from moments.services.extraction import ExtractionManager
from moments.types import ExtractionStatus

_FILES = 8
_WORK_SECONDS = 0.05


class _ConcurrencyProbe:
    """Stands in for create_renditions; records peak simultaneous calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self.peak = 0

    def __call__(self, src: Path, renditions: list[images.Rendition]) -> bool:
        with self._lock:
            self._active += 1
            self.peak = max(self.peak, self._active)

        time.sleep(_WORK_SECONDS)

        with self._lock:
            self._active -= 1
        return True


def _album(tmp_albums_dir: Path) -> None:
    album = tmp_albums_dir / "many"
    album.mkdir()
    for i in range(_FILES):
        Image.new("RGB", (20, 20)).save(album / f"{i}.jpg")


def _extract(config: Config) -> dict[str, object]:
    manager = ExtractionManager(config)
    manager.start("many")
    for _ in range(200):
        status = manager.get_status("many")
        if status["status"] != ExtractionStatus.RUNNING:
            return status
        time.sleep(0.02)
    raise AssertionError("extraction did not finish")


@pytest.mark.parametrize(("threads", "expect_parallel"), [(4, True), (1, False)])
def test_extraction_respects_num_threads(
    tmp_albums_dir: Path,
    tmp_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    threads: int,
    expect_parallel: bool,
) -> None:
    """num_threads=4 → files processed concurrently (≤4); num_threads=1 → one at a time."""
    _album(tmp_albums_dir)
    probe = _ConcurrencyProbe()
    monkeypatch.setattr(images, "create_renditions", probe)
    config = Config(source_dir=tmp_albums_dir, data_dir=tmp_data_dir, num_threads=threads)

    status = _extract(config)

    assert status["status"] == ExtractionStatus.IDLE
    assert status["done"] == status["total"] == _FILES
    assert probe.peak <= threads
    assert (probe.peak > 1) == expect_parallel


def test_failing_file_skipped(
    tmp_albums_dir: Path, tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One file raising doesn't abort the album; others still indexed."""
    _album(tmp_albums_dir)
    real = images.extract_exif

    def flaky(path: Path) -> dict[str, object]:
        if path.name == "3.jpg":
            raise OSError("boom")
        return real(path)

    monkeypatch.setattr(images, "extract_exif", flaky)
    config = Config(source_dir=tmp_albums_dir, data_dir=tmp_data_dir, num_threads=4)

    status = _extract(config)

    from moments.storage import data

    items = data.load_index(data.album_index_path(tmp_data_dir, "many")) or []
    assert status["status"] == ExtractionStatus.IDLE
    assert sorted(i["path"] for i in items) == sorted(f"{n}.jpg" for n in range(_FILES) if n != 3)
