"""Pure conversion logic.  NO print / UI / Rich.

Progress  → yield dict
Errors    → raise ConversionError | FFmpegNotFoundError
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from collections.abc import Generator
from pathlib import Path

from h1tool.core.exceptions import ConversionError, FFmpegNotFoundError

ProgressEvent = dict

AUDIO_FORMATS = frozenset(
    {"mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus"}
)
VIDEO_FORMATS = frozenset(
    {"mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "mpeg"}
)
IMAGE_FORMATS = frozenset(
    {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "ico"}
)
ALL_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS | IMAGE_FORMATS

_AUDIO_CODECS: dict[str, str] = {
    "mp3": "libmp3lame",
    "aac": "aac",
    "ogg": "libvorbis",
    "opus": "libopus",
    "flac": "flac",
    "wav": "pcm_s16le",
    "m4a": "aac",
    "wma": "wmav2",
}


def _ensure_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise FFmpegNotFoundError(
            "ffmpeg not found in PATH.  Install: https://ffmpeg.org/download.html"
        )


def _detect_type(path: Path) -> str:
    ext = path.suffix[1:].lower()
    if ext in AUDIO_FORMATS:
        return "audio"
    if ext in VIDEO_FORMATS:
        return "video"
    if ext in IMAGE_FORMATS:
        return "image"
    return "unknown"


def _probe_duration(path: Path) -> float | None:
    """Return media duration in seconds via ffprobe, or None."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return None


def _build_cmd(input_path: Path, output_path: Path) -> list[str]:
    fmt = output_path.suffix[1:].lower()
    cmd: list[str] = ["ffmpeg", "-i", str(input_path)]

    if fmt in AUDIO_FORMATS:
        codec = _AUDIO_CODECS.get(fmt, "copy")
        cmd += ["-vn", "-acodec", codec]
        if fmt == "mp3":
            cmd += ["-q:a", "0"]
    elif fmt in VIDEO_FORMATS:
        cmd += [
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
        ]

    cmd += ["-progress", "pipe:1", "-nostats"]
    cmd += ["-y", str(output_path)]
    return cmd


def _run_ffmpeg_with_progress(
    cmd: list[str],
    duration: float | None,
    label: str,
) -> Generator[ProgressEvent, None, None]:
    """Spawn ffmpeg, parse ``-progress pipe:1`` output, yield events."""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError("ffmpeg not found in PATH") from exc

    assert proc.stdout is not None  # noqa: S101
    assert proc.stderr is not None  # noqa: S101

    stderr_lines: list[str] = []
    stderr_t = threading.Thread(
        target=lambda: stderr_lines.extend(proc.stderr),  # type: ignore[union-attr]
        daemon=True,
    )
    stderr_t.start()

    for raw_line in proc.stdout:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("out_time_us=") and duration and duration > 0:
            try:
                us = int(line.split("=", 1)[1])
                seconds = us / 1_000_000
                pct = min((seconds / duration) * 100.0, 99.9)
                yield {"status": "converting", "percent": pct, "label": label}
            except (ValueError, ZeroDivisionError):
                pass
        elif line == "progress=end":
            break

    proc.wait()
    stderr_t.join(timeout=3)

    if proc.returncode != 0:
        err_text = "".join(stderr_lines)[:500]
        raise ConversionError(f"ffmpeg exited {proc.returncode}: {err_text}")

    yield {"status": "completed", "percent": 100.0, "label": label}


def convert_file(
    input_path: Path,
    output_format: str,
    output_dir: Path,
) -> Generator[ProgressEvent, None, None]:
    """Convert a single file.  Yields ProgressEvent dicts."""
    _ensure_ffmpeg()

    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise ConversionError(f"File not found: {input_path}")
    if not input_path.is_file():
        raise ConversionError(f"Not a file: {input_path}")

    fmt = output_format.lower().lstrip(".")
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in ALL_FORMATS:
        raise ConversionError(
            f"Unsupported format: {fmt}  "
            f"(known: {', '.join(sorted(ALL_FORMATS))})"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}.{fmt}"
    label = f"{input_path.name} → {fmt.upper()}"

    yield {"status": "started", "filename": input_path.name, "label": label}

    if fmt in IMAGE_FORMATS:
        cmd = ["ffmpeg", "-i", str(input_path), "-y", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConversionError(
                f"Image conversion failed: {result.stderr[:500]}"
            )
        yield {
            "status": "completed",
            "percent": 100.0,
            "label": label,
            "output": str(output_path),
        }
        return

    duration = _probe_duration(input_path)
    cmd = _build_cmd(input_path, output_path)

    for event in _run_ffmpeg_with_progress(cmd, duration, label):
        if event["status"] == "completed":
            event["output"] = str(output_path)
        yield event


def batch_convert(
    input_dir: Path,
    output_format: str,
    output_dir: Path,
) -> Generator[ProgressEvent, None, None]:
    """Batch-convert every file in *input_dir*."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise ConversionError(f"Directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise ConversionError(f"Not a directory: {input_dir}")

    files = sorted(f for f in input_dir.iterdir() if f.is_file())
    if not files:
        raise ConversionError(f"No files in: {input_dir}")

    total = len(files)
    yield {"status": "batch_started", "total": total}

    ok = fail = 0
    for idx, fp in enumerate(files, 1):
        yield {
            "status": "batch_file",
            "current": idx,
            "total": total,
            "filename": fp.name,
        }
        try:
            yield from convert_file(fp, output_format, output_dir)
            ok += 1
        except (ConversionError, FFmpegNotFoundError) as exc:
            fail += 1
            yield {"status": "file_error", "filename": fp.name, "error": str(exc)}

    yield {"status": "batch_completed", "success": ok, "failed": fail, "total": total}


def convert_to_mp3(
    input_path: Path,
    output_dir: Path,
) -> Generator[ProgressEvent, None, None]:
    """Shortcut: convert file or whole directory to MP3."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise ConversionError(f"Path not found: {input_path}")

    if input_path.is_file():
        yield from convert_file(input_path, "mp3", output_dir)
    elif input_path.is_dir():
        yield from batch_convert(input_path, "mp3", output_dir)
    else:
        raise ConversionError(f"Invalid path: {input_path}")
