"""Tests for core/converters.py — validation & edge cases.

NOTE: These tests do NOT invoke ffmpeg. They test argument
validation, format detection, and error paths.
"""

import pytest

from h1tool.core.converters import (
    ALL_FORMATS,
    AUDIO_FORMATS,
    IMAGE_FORMATS,
    VIDEO_FORMATS,
    _detect_type,
    convert_file,
    batch_convert,
    convert_to_mp3,
)
from h1tool.core.exceptions import ConversionError, FFmpegNotFoundError


def test_format_sets_no_overlap():
    """Audio, video, image sets should not overlap (except jpeg/jpg)."""
    assert not (AUDIO_FORMATS & VIDEO_FORMATS)
    assert not (AUDIO_FORMATS & IMAGE_FORMATS - {"jpeg"})
    assert not (VIDEO_FORMATS & IMAGE_FORMATS)


def test_detect_type_audio(tmp_path):
    f = tmp_path / "song.mp3"
    f.touch()
    assert _detect_type(f) == "audio"


def test_detect_type_video(tmp_path):
    f = tmp_path / "clip.mp4"
    f.touch()
    assert _detect_type(f) == "video"


def test_detect_type_image(tmp_path):
    f = tmp_path / "pic.png"
    f.touch()
    assert _detect_type(f) == "image"


def test_detect_type_unknown(tmp_path):
    f = tmp_path / "data.xyz"
    f.touch()
    assert _detect_type(f) == "unknown"


def test_convert_file_missing_input(tmp_path):
    gen = convert_file(tmp_path / "nope.mp4", "mp3", tmp_path / "out")
    with pytest.raises(ConversionError, match="File not found"):
        list(gen)


def test_convert_file_not_a_file(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    gen = convert_file(d, "mp3", tmp_path / "out")
    with pytest.raises(ConversionError, match="Not a file"):
        list(gen)


def test_convert_file_unsupported_format(tmp_path):
    f = tmp_path / "test.mp4"
    f.write_bytes(b"\x00")
    gen = convert_file(f, "xyzzy", tmp_path / "out")
    with pytest.raises(ConversionError, match="Unsupported format"):
        list(gen)


def test_convert_file_no_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr("h1tool.core.converters.shutil.which", lambda _: None)
    f = tmp_path / "test.mp4"
    f.write_bytes(b"\x00")
    gen = convert_file(f, "mp3", tmp_path / "out")
    with pytest.raises(FFmpegNotFoundError):
        list(gen)


def test_batch_convert_missing_dir(tmp_path):
    gen = batch_convert(tmp_path / "nope", "mp3", tmp_path / "out")
    with pytest.raises(ConversionError, match="Directory not found"):
        list(gen)


def test_batch_convert_empty_dir(empty_dir, tmp_path):
    gen = batch_convert(empty_dir, "mp3", tmp_path / "out")
    with pytest.raises(ConversionError, match="No files"):
        list(gen)


def test_convert_to_mp3_missing(tmp_path):
    gen = convert_to_mp3(tmp_path / "ghost.wav", tmp_path / "out")
    with pytest.raises(ConversionError, match="Path not found"):
        list(gen)