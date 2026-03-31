"""Verify custom exceptions hierarchy."""

import pytest

from h1tool.core.exceptions import (
    ConversionError,
    DownloadError,
    FFmpegNotFoundError,
    H1ToolError,
    SpotDLNotFoundError,
    SpotifyError,
)


@pytest.mark.parametrize(
    "exc_cls",
    [
        DownloadError,
        FFmpegNotFoundError,
        ConversionError,
        SpotifyError,
        SpotDLNotFoundError,
    ],
)
def test_all_inherit_from_base(exc_cls):
    assert issubclass(exc_cls, H1ToolError)


def test_exception_message():
    exc = DownloadError("network timeout")
    assert str(exc) == "network timeout"


def test_exception_is_catchable_as_base():
    with pytest.raises(H1ToolError):
        raise ConversionError("bad format")