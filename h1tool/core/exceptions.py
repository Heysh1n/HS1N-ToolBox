"""Custom exceptions for h1tool core.

Rule: core NEVER prints to console. All errors → raise.
"""


class H1ToolError(Exception):
    """Base for all h1tool errors."""


class DownloadError(H1ToolError):
    """Download failed (network, yt-dlp, invalid URL, …)."""


class FFmpegNotFoundError(H1ToolError):
    """ffmpeg binary not found in system PATH."""


class ConversionError(H1ToolError):
    """Media conversion failed."""


class SpotifyError(H1ToolError):
    """Spotify download failed."""


class SpotifyRateLimitError(SpotifyError):
    """Spotify API rate limit exceeded — IP banned temporarily."""


class SpotDLNotFoundError(H1ToolError):
    """spotdl binary not found in system PATH."""