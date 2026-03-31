"""Tests for core/spotify.py — validation and URL parsing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from h1tool.core.exceptions import SpotDLNotFoundError, SpotifyError
from h1tool.core.spotify import _clean_spotify_url, download_spotify, is_spotify_url


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6", True),
        ("https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3", True),
        ("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M", True),
        ("https://open.spotify.com/intl-ru/track/abc123", True),
        ("https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg", True),
        # URLs with query params should still match
        (
            "https://open.spotify.com/album/ABC?highlight=spotify:track:XYZ",
            True,
        ),
        ("https://open.spotify.com/track/ABC?si=def123", True),
        # Non-spotify
        ("https://youtube.com/watch?v=dQw4w9", False),
        ("not a url", False),
        ("", False),
    ],
)
def test_is_spotify_url(url: str, expected: bool):
    assert is_spotify_url(url) is expected


@pytest.mark.parametrize(
    "raw,clean",
    [
        # highlight param (the bug)
        (
            "https://open.spotify.com/album/6FQixEQWNUYSu7FPuKLCDN"
            "?highlight=spotify:track:4e54GhjU0PAXwbGvbwAPz6",
            "https://open.spotify.com/album/6FQixEQWNUYSu7FPuKLCDN",
        ),
        # si param
        (
            "https://open.spotify.com/track/ABC?si=xyz123",
            "https://open.spotify.com/track/ABC",
        ),
        # intl prefix + query
        (
            "https://open.spotify.com/intl-ru/track/ABC?si=xyz",
            "https://open.spotify.com/intl-ru/track/ABC",
        ),
        # already clean
        (
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        ),
        # leading/trailing whitespace
        (
            "  https://open.spotify.com/album/ABC?x=1  ",
            "https://open.spotify.com/album/ABC",
        ),
    ],
)
def test_clean_spotify_url(raw: str, clean: str):
    assert _clean_spotify_url(raw) == clean


def test_download_spotify_no_spotdl():
    with patch("h1tool.core.spotify.shutil.which", return_value=None):
        gen = download_spotify(
            "https://open.spotify.com/track/abc123",
            Path("/tmp/out"),
        )
        with pytest.raises(SpotDLNotFoundError):
            list(gen)


def test_download_spotify_bad_url():
    with patch("h1tool.core.spotify.shutil.which", return_value="/usr/bin/spotdl"):
        gen = download_spotify("not-a-spotify-url", Path("/tmp/out"))
        with pytest.raises(SpotifyError, match="Not a valid"):
            list(gen)


def test_download_spotify_cleans_url_before_spotdl():
    """Verify that the highlight param is stripped before reaching spotdl."""
    with patch("h1tool.core.spotify.shutil.which", return_value="/usr/bin/spotdl"):
        dirty = (
            "https://open.spotify.com/album/6FQixEQWNUYSu7FPuKLCDN"
            "?highlight=spotify:track:4e54GhjU0PAXwbGvbwAPz6"
        )
        gen = download_spotify(dirty, Path("/tmp/out"))

        # First yield is "started" — check the cleaned URL
        event = next(gen)
        assert event["status"] == "started"
        assert "highlight" not in event["url"]
        assert "track" not in event["url"]
        assert "album/6FQixEQWNUYSu7FPuKLCDN" in event["url"]