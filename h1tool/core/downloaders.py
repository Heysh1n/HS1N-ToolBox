"""Pure download logic.  NO print / UI / Rich / Loader.

Progress  → yield dict
Errors    → raise DownloadError
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Generator
from pathlib import Path

from h1tool.core.exceptions import DownloadError

ProgressEvent = dict

# ── Cookies file (optional, place next to project root) ──────
_COOKIES_FILE = Path("cookies.txt")

# ── YouTube client spoofing ──────────────────────────────────
_YT_EXTRACTOR_ARGS = {
    "youtube": {
        "player_client": ["android", "ios", "web"],
    },
}


def _base_opts() -> dict:
    """Shared yt-dlp options: quiet mode, client spoofing, cookies."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extractor_args": _YT_EXTRACTOR_ARGS,
    }
    if _COOKIES_FILE.exists():
        opts["cookiefile"] = str(_COOKIES_FILE.resolve())
    return opts


def _run_yt_dlp(url: str, ydl_opts: dict) -> Generator[ProgressEvent, None, None]:
    """Run yt-dlp in a background thread, yield progress events."""
    try:
        from yt_dlp import YoutubeDL  # noqa: WPS433
    except ImportError as exc:
        raise DownloadError(
            "yt-dlp is not installed. Run:  pip install yt-dlp"
        ) from exc

    events: queue.Queue[ProgressEvent] = queue.Queue()
    error_slot: list[BaseException | None] = [None]

    def _hook(d: dict) -> None:
        status = d.get("status")
        if status == "downloading":
            raw = d.get("_percent_str", "0%").replace("%", "").strip()
            try:
                pct = min(float(raw), 100.0)
            except ValueError:
                pct = 0.0
            events.put({
                "status": "downloading",
                "percent": pct,
                "speed": d.get("_speed_str", ""),
                "eta": d.get("_eta_str", ""),
            })
        elif status == "finished":
            events.put({
                "status": "processing",
                "percent": 100.0,
                "filename": d.get("filename", ""),
            })

    # Merge base opts → user opts → hooks (hooks always last)
    merged = {**_base_opts(), **ydl_opts, "progress_hooks": [_hook]}

    def _worker() -> None:
        try:
            with YoutubeDL(merged) as ydl:
                ydl.download([url])
            events.put({"status": "completed", "percent": 100.0})
        except Exception as exc:  # noqa: BLE001
            error_slot[0] = exc
            events.put({"status": "error", "message": str(exc)})

    thread = threading.Thread(target=_worker, daemon=True)

    yield {"status": "started", "url": url}
    thread.start()

    while thread.is_alive() or not events.empty():
        try:
            event = events.get(timeout=0.15)
        except queue.Empty:
            continue

        if event["status"] == "error":
            raise DownloadError(event["message"])

        yield event

        if event["status"] == "completed":
            break

    thread.join(timeout=5.0)

    if error_slot[0] is not None:
        raise DownloadError(str(error_slot[0])) from error_slot[0]


def download_video(
    url: str,
    output_dir: Path,
    resolution: str = "best",
    format_ext: str = "mp4",
    playlist: bool = False,
) -> Generator[ProgressEvent, None, None]:
    """Download video.  Yields ProgressEvent dicts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if resolution == "best":
        fmt = f"bestvideo[ext={format_ext}]+bestaudio/best"
    else:
        fmt = (
            f"bestvideo[ext={format_ext}][height<={resolution}]"
            f"+bestaudio/best"
        )

    ydl_opts = {
        "format": fmt,
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "merge_output_format": format_ext,
        "noplaylist": not playlist,
    }

    yield from _run_yt_dlp(url, ydl_opts)


def download_audio(
    url: str,
    output_dir: Path,
    audio_format: str = "mp3",
    quality: str = "0",
    playlist: bool = False,
) -> Generator[ProgressEvent, None, None]:
    """Download audio only.  Same yield/raise contract as download_video."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": quality,
            },
        ],
        "noplaylist": not playlist,
    }

    yield from _run_yt_dlp(url, ydl_opts)
