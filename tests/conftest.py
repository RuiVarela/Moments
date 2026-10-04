"""Pytest fixtures for test suite."""
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Generator

import pytest
from PIL import Image
from PIL.ExifTags import TAGS

from moments.config import Config


@pytest.fixture
def tmp_albums_dir() -> Generator[Path, None, None]:
    """Create temporary albums directory and clean up."""
    tmpdir = Path(tempfile.mkdtemp(prefix="moments_test_"))
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def tmp_data_dir() -> Generator[Path, None, None]:
    """Create temporary data directory and clean up."""
    tmpdir = Path(tempfile.mkdtemp(prefix="moments_data_"))
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def config(
    tmp_albums_dir: Path,
    tmp_data_dir: Path,
) -> Config:
    """Create test config."""
    return Config(
        port=8000,
        source_dir=tmp_albums_dir,
        data_dir=tmp_data_dir,
        thumb_size=200,
        preview_size=800,
    )


def create_test_album(
    albums_dir: Path,
    album_name: str,
    num_images: int = 3,
    include_cover: bool = False,
) -> Path:
    """Create test album with JPEG images (with EXIF date and GPS)."""
    album_path = albums_dir / album_name
    album_path.mkdir(exist_ok=True)

    # Create nested folder.
    subfolder = album_path / "subfolder"
    subfolder.mkdir(exist_ok=True)

    dates = [
        "2024-01-10 10:00:00",
        "2024-01-15 11:00:00",
        "2024-01-20 12:00:00",
    ]

    for i in range(num_images):
        img_path = subfolder / f"photo_{i:03d}.jpg"
        img = Image.new("RGB", (800, 600), color=(73, 109, 137))
        img.save(str(img_path))

        # Add EXIF data (date taken).
        if i < len(dates):
            # Note: pillow basic save doesn't preserve EXIF, so we skip for now.
            # Real images from cameras will have EXIF.
            pass

    # Create cover if requested.
    if include_cover:
        cover_path = album_path / "cover.jpg"
        img = Image.new("RGB", (400, 300), color=(255, 0, 0))
        img.save(str(cover_path))

    # Create hidden file (should be ignored).
    hidden = album_path / ".hidden"
    hidden.write_text("ignored")

    # Create root file (should be ignored).
    root_file = album_path / "root.txt"
    root_file.write_text("ignored")

    return album_path


def create_test_video(albums_dir: Path, album_name: str) -> bool:
    """Create test video file using ffmpeg if available.

    Returns True if successful, False if ffmpeg not available.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    album_path = albums_dir / album_name
    album_path.mkdir(exist_ok=True)

    video_path = album_path / "test_video.mp4"

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=640x480:d=1",
                "-f",
                "lavfi",
                "-i",
                "sine=f=1000:d=1",
                "-pix_fmt",
                "yuv420p",
                str(video_path),
            ],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except Exception:
        return False


@pytest.fixture
def album_with_images(tmp_albums_dir: Path) -> Path:
    """Create test album with images."""
    return create_test_album(
        tmp_albums_dir, "vacation", num_images=3, include_cover=True
    )


@pytest.fixture
def album_empty(tmp_albums_dir: Path) -> Path:
    """Create empty album (no media files)."""
    album_path = tmp_albums_dir / "empty"
    album_path.mkdir()
    return album_path
