"""Tests for config loading."""
import json
import os
from pathlib import Path

import pytest

from moments.config import Config, load_config


def test_load_config_from_file(tmp_path: Path) -> None:
    """Test loading config from explicit JSON file."""
    config_file = tmp_path / "config.json"
    source_dir = tmp_path / "source"
    data_dir = tmp_path / "data"
    source_dir.mkdir()
    data_dir.mkdir()

    config_file.write_text(
        json.dumps({
            "port": 9000,
            "source_dir": str(source_dir),
            "data_dir": str(data_dir),
        })
    )

    cfg = load_config(config_file)
    assert cfg.port == 9000
    assert cfg.source_dir == source_dir
    assert cfg.data_dir == data_dir


def test_load_config_from_env_var(tmp_path: Path, monkeypatch) -> None:
    """Test loading from MOMENTS_CONFIG env var."""
    config_file = tmp_path / "custom.json"
    source_dir = tmp_path / "source"
    data_dir = tmp_path / "data"
    source_dir.mkdir()
    data_dir.mkdir()

    config_file.write_text(
        json.dumps({
            "port": 8001,
            "source_dir": str(source_dir),
            "data_dir": str(data_dir),
        })
    )

    monkeypatch.setenv("MOMENTS_CONFIG", str(config_file))
    cfg = load_config()
    assert cfg.port == 8001


def test_load_config_from_cwd_default(
    tmp_path: Path, monkeypatch
) -> None:
    """Test loading config.json from cwd."""
    source_dir = tmp_path / "source"
    data_dir = tmp_path / "data"
    source_dir.mkdir()
    data_dir.mkdir()

    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "source_dir": str(source_dir),
            "data_dir": str(data_dir),
        })
    )

    monkeypatch.chdir(tmp_path)
    # Clear env var to use default.
    monkeypatch.delenv("MOMENTS_CONFIG", raising=False)

    cfg = load_config()
    assert cfg.source_dir == source_dir
    assert cfg.data_dir == data_dir


def test_load_config_defaults(tmp_path: Path) -> None:
    """Test config defaults (port, sizes)."""
    config_file = tmp_path / "config.json"
    source_dir = tmp_path / "source"
    data_dir = tmp_path / "data"
    source_dir.mkdir()
    data_dir.mkdir()

    # Minimal config, no optional fields.
    config_file.write_text(
        json.dumps({
            "source_dir": str(source_dir),
            "data_dir": str(data_dir),
        })
    )

    cfg = load_config(config_file)
    assert cfg.port == 8000  # default
    assert cfg.thumb_size == 200  # default
    assert cfg.preview_size == 800  # default


def test_load_config_missing_file() -> None:
    """Test error on missing config file."""
    with pytest.raises(FileNotFoundError, match="config.json"):
        load_config(Path("/nonexistent/config.json"))


def test_load_config_missing_source_dir(tmp_path: Path) -> None:
    """Test error on missing source_dir."""
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "source_dir": "/nonexistent/source",
            "data_dir": str(tmp_path / "data"),
        })
    )

    with pytest.raises(ValueError, match="source_dir"):
        load_config(config_file)


def test_load_config_invalid_sizes(tmp_path: Path) -> None:
    """Test error on invalid sizes."""
    config_file = tmp_path / "config.json"
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    config_file.write_text(
        json.dumps({
            "source_dir": str(source_dir),
            "data_dir": str(tmp_path / "data"),
            "thumb_size": 0,  # Invalid
        })
    )

    with pytest.raises(ValueError, match="positive"):
        load_config(config_file)


def test_config_direct_construction(tmp_path: Path) -> None:
    """Test that Config still works with direct construction."""
    source_dir = tmp_path / "source"
    data_dir = tmp_path / "data"
    source_dir.mkdir()
    data_dir.mkdir()

    cfg = Config(
        port=7000,
        source_dir=source_dir,
        data_dir=data_dir,
    )
    assert cfg.port == 7000
