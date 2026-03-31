"""Tests for utils/env_checker.py — pure checks, no side effects."""

from unittest.mock import patch

from h1tool.utils.env_checker import (
    check_ffmpeg,
    check_spotdl,
    check_yt_dlp,
    get_ffmpeg_path,
)


def test_check_ffmpeg_found():
    with patch("h1tool.utils.env_checker.shutil.which", return_value="/usr/bin/ffmpeg"):
        assert check_ffmpeg() is True


def test_check_ffmpeg_missing():
    with patch("h1tool.utils.env_checker.shutil.which", return_value=None):
        assert check_ffmpeg() is False


def test_get_ffmpeg_path_found():
    with patch("h1tool.utils.env_checker.shutil.which", return_value="/usr/bin/ffmpeg"):
        p = get_ffmpeg_path()
        assert p is not None
        assert p.name == "ffmpeg"


def test_get_ffmpeg_path_missing():
    with patch("h1tool.utils.env_checker.shutil.which", return_value=None):
        assert get_ffmpeg_path() is None


def test_check_spotdl_found():
    with patch("h1tool.utils.env_checker.shutil.which", return_value="/usr/bin/spotdl"):
        assert check_spotdl() is True


def test_check_spotdl_missing():
    with patch("h1tool.utils.env_checker.shutil.which", return_value=None):
        assert check_spotdl() is False


def test_check_yt_dlp_importable():
    with patch.dict("sys.modules", {"yt_dlp": __import__("os")}):
        assert check_yt_dlp() is True


def test_check_yt_dlp_not_installed():
    import sys
    saved = sys.modules.pop("yt_dlp", None)
    try:
        with patch.dict("sys.modules", {"yt_dlp": None}):
            # force ImportError
            with patch("builtins.__import__", side_effect=ImportError):
                assert check_yt_dlp() is False
    finally:
        if saved is not None:
            sys.modules["yt_dlp"] = saved