"""Music search across multiple platforms.

TODO: Implement fallback when Spotify is rate-limited.

Strategy:
1. Extract metadata from Spotify URL (track name, artist, album)
2. Search on fallback platforms in order:
   - YouTube Music (via yt-dlp)
   - SoundCloud (via yt-dlp)
   - Deezer (via deemix if available)
   - Bandcamp (via yt-dlp)
3. Download from first match

Example flow:
  Spotify URL → metadata → "Artist - Track Name" → YouTube Music search → download

Implementation ideas:
  - Use Spotify Web API (with user keys) just for metadata, not download
  - Use yt-dlp search: `ytsearch1:Artist - Track Name`
  - Compare duration/title similarity to verify correct track
"""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrackMetadata:
    """Metadata extracted from a music URL or search."""

    title: str
    artist: str
    album: str | None = None
    duration_sec: int | None = None
    isrc: str | None = None


def search_youtube_music(query: str) -> str | None:
    """Search YouTube Music, return video URL if found.

    TODO: Implement using yt-dlp search.

    Example:
        yt-dlp "ytsearch1:Rick Astley Never Gonna Give You Up" --get-url
    """
    raise NotImplementedError("YouTube Music search not yet implemented")


def search_soundcloud(query: str) -> str | None:
    """Search SoundCloud, return track URL if found.

    TODO: Implement using yt-dlp search.

    Example:
        yt-dlp "scsearch1:Rick Astley Never Gonna Give You Up" --get-url
    """
    raise NotImplementedError("SoundCloud search not yet implemented")


def download_with_fallback(
    spotify_url: str,
    output_dir: Path,
    audio_format: str = "mp3",
) -> Generator[dict, None, None]:
    """Try Spotify first, fallback to other platforms on rate limit.

    TODO: Implement full fallback chain.

    Yields progress events like other downloaders.
    """
    raise NotImplementedError("Fallback download not yet implemented")