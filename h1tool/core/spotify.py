"""Spotify download logic.  NO print / UI.

Progress  → yield dict
Errors    → raise SpotifyError | SpotDLNotFoundError

TODO: Implement fallback providers when Spotify rate limits:
  - YouTube Music search by metadata
  - SoundCloud search
  - Deezer (with deemix)
  - Bandcamp
"""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from h1tool.core.exceptions import SpotDLNotFoundError, SpotifyError

ProgressEvent = dict

_SPOTIFY_RE = re.compile(
    r"^https?://open\.spotify\.com(/intl-[a-zA-Z]+)?/"
    r"(track|album|playlist|artist)/[a-zA-Z0-9]+",
)

# Known error patterns
_RATE_LIMIT_PATTERNS = [
    "rate/request limit",
    "rate limit",
    "429",
    "retry will occur after",
    "too many requests",
]


def _ensure_spotdl() -> None:
    if not shutil.which("spotdl"):
        raise SpotDLNotFoundError(
            "spotdl not found in PATH.  Install: pip install spotdl"
        )


def is_spotify_url(text: str) -> bool:
    """Return True if *text* looks like a Spotify URL."""
    return bool(_SPOTIFY_RE.match(text.strip()))


def _clean_spotify_url(url: str) -> str:
    """Strip query params and fragments that confuse spotdl."""
    parsed = urlparse(url.strip())
    clean = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        "",
        "",
        "",
    ))
    return clean


def _read_stream(stream, bucket: list[str]) -> None:
    """Read all lines from a stream into a list."""
    try:
        for line in stream:
            bucket.append(line)
    except ValueError:
        pass


def _is_rate_limited(text: str) -> bool:
    """Check if error text indicates Spotify rate limiting."""
    lower = text.lower()
    return any(pattern in lower for pattern in _RATE_LIMIT_PATTERNS)


def _extract_retry_time(text: str) -> str | None:
    """Extract retry time from rate limit message."""
    match = re.search(r"after[:\s]*(\d+)\s*s", text.lower())
    if match:
        seconds = int(match.group(1))
        hours = seconds // 3600
        if hours > 0:
            return f"{hours}h"
        minutes = seconds // 60
        if minutes > 0:
            return f"{minutes}m"
        return f"{seconds}s"
    return None


def download_spotify(
    url: str,
    output_dir: Path,
    audio_format: str = "mp3",
) -> Generator[ProgressEvent, None, None]:
    """Download from Spotify via spotdl.  Yields ProgressEvent dicts."""
    _ensure_spotdl()

    url = url.strip()
    if not is_spotify_url(url):
        raise SpotifyError(f"Not a valid Spotify URL: {url}")

    clean_url = _clean_spotify_url(url)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "spotdl", "download", clean_url,
        "--output", str(output_dir),
        "--format", audio_format,
    ]

    yield {"status": "started", "url": clean_url}

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        raise SpotDLNotFoundError("spotdl not found in PATH") from exc

    assert proc.stdout is not None
    assert proc.stderr is not None

    stderr_lines: list[str] = []
    stderr_t = threading.Thread(
        target=_read_stream,
        args=(proc.stderr, stderr_lines),
        daemon=True,
    )
    stderr_t.start()

    for raw_line in proc.stdout:
        line = raw_line.strip()
        if not line:
            continue

        # Check for rate limit in stdout
        if _is_rate_limited(line):
            retry = _extract_retry_time(line)
            retry_msg = f" (retry in {retry})" if retry else ""
            raise SpotifyError(
                f"Spotify rate limit hit{retry_msg}. "
                "Try: VPN, mobile hotspot, or wait 24h. "
                "Your API keys are fine — Spotify banned your IP."
            )

        # Skip Rich traceback noise
        if any(skip in line for skip in ("Traceback", "│", "╭", "╰", "╮", "╯")):
            continue

        m_found = re.search(r"Found\s+(\d+)\s+song", line)
        if m_found:
            tracks_found = int(m_found.group(1))
            yield {
                "status": "info",
                "message": f"Found {tracks_found} song(s)",
                "total_tracks": tracks_found,
            }
            continue

        if line.lower().startswith("downloaded") or "complete" in line.lower():
            yield {"status": "track_done", "message": line}
            continue
        if line.lower().startswith("skipping"):
            yield {"status": "track_skip", "message": line}
            continue

        if "error" in line.lower() or "exception" in line.lower():
            yield {"status": "info", "message": f"⚠ {line}"}
            continue

        m_pct = re.search(r"(\d{1,3})%", line)
        if m_pct:
            pct = min(int(m_pct.group(1)), 100)
            yield {"status": "downloading", "percent": float(pct)}
            continue

        yield {"status": "info", "message": line}

    proc.wait()
    stderr_t.join(timeout=5)

    # Check stderr for rate limit
    stderr_text = "".join(stderr_lines)
    if _is_rate_limited(stderr_text):
        retry = _extract_retry_time(stderr_text)
        retry_msg = f" (retry in {retry})" if retry else ""
        raise SpotifyError(
            f"Spotify rate limit hit{retry_msg}. "
            "Try: VPN, mobile hotspot, or wait 24h. "
            "Your API keys are fine — Spotify banned your IP."
        )

    if proc.returncode != 0:
        useful_lines = [
            ln.strip()
            for ln in stderr_lines
            if ln.strip()
            and not any(c in ln for c in ("│", "╭", "╰", "╮", "╯", "───"))
            and not ln.strip().startswith("File ")
        ]
        short_err = useful_lines[-1] if useful_lines else stderr_text[:300]

        raise SpotifyError(
            f"spotdl exited {proc.returncode}: {short_err or 'unknown error'}"
        )

    yield {
        "status": "completed",
        "percent": 100.0,
        "output_dir": str(output_dir),
    }