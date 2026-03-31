"""Shared fixtures for all tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_file(tmp_path: Path) -> Path:
    """Create a tiny dummy file and return its path."""
    f = tmp_path / "sample.txt"
    f.write_text("hello")
    return f


@pytest.fixture()
def tmp_dir_with_files(tmp_path: Path) -> Path:
    """Create a temp directory with 3 dummy files."""
    for name in ("a.mp4", "b.wav", "c.png"):
        (tmp_path / name).write_bytes(b"\x00" * 64)
    return tmp_path


@pytest.fixture()
def empty_dir(tmp_path: Path) -> Path:
    """Return an empty temp directory."""
    d = tmp_path / "empty"
    d.mkdir()
    return d