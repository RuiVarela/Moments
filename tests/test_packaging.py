"""Built wheel must contain the whole app (Docker installs it non-editable)."""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def wheel_names(tmp_path_factory: pytest.TempPathFactory) -> set[str]:
    """Build wheel once; return file names inside it."""
    out = tmp_path_factory.mktemp("wheel")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(out), str(_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    wheel = next(out.glob("moments-*.whl"))
    with zipfile.ZipFile(wheel) as zf:
        return set(zf.namelist())


@pytest.mark.parametrize(
    "path",
    [
        "moments/__main__.py",
        "moments/routes/albums.py",
        "moments/services/extraction.py",
        "moments/storage/source.py",
        "moments/drivers/images.py",
        "moments/static/index.html",
        "moments/static/js/main.js",
        "moments/static/js/components/media-tile.js",
        "moments/static/css/album.css",
        "moments/static/favicon.ico",
        "moments/py.typed",
    ],
)
def test_wheel_contains(wheel_names: set[str], path: str) -> None:
    """Subpackages + static frontend ship in the wheel."""
    assert path in wheel_names
