"""Environment checks.  No UI — returns booleans / Path / None."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolStatus:
    """Result of a tool health check."""

    available: bool
    path: str | None = None
    warning: str | None = None
    hints: list[str] = field(default_factory=list)


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is reachable in PATH."""
    return shutil.which("ffmpeg") is not None


def get_ffmpeg_path() -> Path | None:
    """Return the resolved ffmpeg path or None."""
    p = shutil.which("ffmpeg")
    return Path(p) if p else None


def check_yt_dlp() -> bool:
    """Return True if yt-dlp is importable."""
    try:
        import yt_dlp  # noqa: F401

        return True
    except ImportError:
        return False


def check_spotdl() -> bool:
    """Return True if spotdl is reachable in PATH."""
    return shutil.which("spotdl") is not None


def check_spotdl_config() -> ToolStatus:
    """Check if spotdl is installed AND has API credentials configured."""
    path = shutil.which("spotdl")
    if not path:
        return ToolStatus(
            available=False,
            warning="spotdl not found. Install: pip install spotdl",
        )

    config_path = Path.home() / ".spotdl" / "config.json"
    if not config_path.exists():
        return ToolStatus(
            available=True,
            path=path,
            warning="No spotdl config found. You'll hit rate limits fast.",
            hints=[
                "1. Go to https://developer.spotify.com/dashboard",
                "2. Create App → set redirect URI: http://localhost:8888/callback",
                "3. Run: spotdl --client-id YOUR_ID --client-secret YOUR_SECRET --generate-config",
            ],
        )

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        client_id = config.get("client_id", "")
        if not client_id or len(client_id) < 10:
            return ToolStatus(
                available=True,
                path=path,
                warning="spotdl config exists but missing Spotify API keys.",
                hints=[
                    "Run: spotdl --client-id YOUR_ID --client-secret YOUR_SECRET --generate-config",
                    "Get keys at: https://developer.spotify.com/dashboard",
                ],
            )
    except (json.JSONDecodeError, OSError):
        pass

    return ToolStatus(available=True, path=path)


def check_js_runtime() -> ToolStatus:
    """Check if a JS runtime (deno/node) is available for yt-dlp."""
    for name in ("deno", "node", "nodejs"):
        p = shutil.which(name)
        if p:
            return ToolStatus(available=True, path=p)

    return ToolStatus(
        available=False,
        warning="No JS runtime found (deno/node). yt-dlp may fail on YouTube.",
        hints=[
            "Option A: curl -fsSL https://deno.land/install.sh | sh",
            "Option B: sudo apt install nodejs",
        ],
    )


def check_yt_dlp_version() -> ToolStatus:
    """Check yt-dlp version freshness."""
    try:
        import yt_dlp  # noqa: WPS433

        version = yt_dlp.version.__version__
        return ToolStatus(available=True, path=version)
    except (ImportError, AttributeError):
        return ToolStatus(
            available=False,
            warning="yt-dlp not installed.",
            hints=["pip install -U yt-dlp"],
        )


def check_cookies_file() -> ToolStatus:
    """Check if cookies.txt exists for YouTube anti-bot bypass."""
    cookies = Path("cookies.txt")
    if cookies.exists():
        return ToolStatus(available=True, path=str(cookies.resolve()))

    return ToolStatus(
        available=False,
        warning="No cookies.txt found. May get 403 errors on YouTube.",
        hints=[
            "1. Install browser extension 'Get cookies.txt LOCALLY'",
            "2. Export cookies from youtube.com",
            "3. Save as cookies.txt in project root",
        ],
    )
