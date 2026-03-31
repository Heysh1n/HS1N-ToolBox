"""File logger — no UI, just writes errors to disk.

Used optionally by any layer that wants to persist error details.
"""

from __future__ import annotations

import datetime
import traceback
from pathlib import Path
from threading import Lock

_LOG_DIR = Path.home() / ".h1tool" / "logs"
_DEFAULT = "h1tool.log"
_lock = Lock()


def log_error(
    error: Exception,
    *,
    context: str | None = None,
    log_file: str = _DEFAULT,
) -> Path:
    """Append an error entry to the log file.  Returns the log path."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = _LOG_DIR / log_file
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tb = traceback.format_exc()

    entry = (
        f"\n[{ts}] {type(error).__name__}: {error}\n"
        f"Context: {context or 'N/A'}\n"
        f"{tb}\n{'─' * 80}\n"
    )

    with _lock, path.open("a", encoding="utf-8") as f:
        f.write(entry)

    return path


def get_log_dir() -> Path:
    """Return (and create if needed) the log directory."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR
