"""CLI interface — the ONLY place where UI lives.

Rules:
  • Typer  — argument parsing (Annotated style)
  • Rich   — progress bars, panels, errors
  • Core   — called as generator, CLI catches yield and paints
  • Logger — every caught core error is persisted to disk
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from h1tool import __version__
from h1tool.utils.logger import log_error

# ── Typer app ────────────────────────────────────────────────
app = typer.Typer(
    name="h1tool",
    help="🎬🎵 HS1N-Toolbox — download & convert any media from the terminal.",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
)
console = Console()

# ── Default paths as module-level constants (avoids B008) ────
_DEFAULT_DOWNLOADS = Path("downloads")
_DEFAULT_CONVERTED = Path("converted")
_DEFAULT_SPOTIFY = Path("downloads/spotify")


# ── Helpers ──────────────────────────────────────────────────

def _die(msg: str, *, hint: str | None = None, exc: Exception | None = None) -> None:
    """Print error + optional hint, log if exception given, then exit(1)."""
    console.print(f"[bold red]✗ {msg}[/bold red]")
    if hint:
        console.print(f"[dim]  ↳ {hint}[/dim]")
    if exc:
        path = log_error(exc, context=msg)
        console.print(f"[dim]  📝 logged → {path}[/dim]")
    raise typer.Exit(1)


def _version_cb(value: bool) -> None:
    if value:
        console.print(f"[bold magenta]h1tool[/bold magenta] v{__version__}")
        raise typer.Exit()


def _consume(gen, label: str) -> None:
    """Generic consumer: drain a core generator, paint Rich progress."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        TextColumn("[dim]{task.fields[extra]}[/dim]"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as prog:
        task = prog.add_task(label, total=100, extra="")

        for ev in gen:
            st = ev.get("status", "")
            match st:
                case "started":
                    if url := ev.get("url"):
                        console.print(f"[cyan]→ {url}[/cyan]")
                case "downloading":
                    prog.update(
                        task,
                        completed=ev.get("percent", 0),
                        extra=ev.get("speed", ""),
                    )
                case "converting":
                    prog.update(task, completed=ev.get("percent", 0))
                case "processing":
                    prog.update(task, completed=100, description=f"{label} · merging")
                case "completed":
                    prog.update(task, completed=100)
                    if out := ev.get("output"):
                        console.print(f"[green]  → {out}[/green]")
                case "batch_started":
                    console.print(f"[cyan]Found {ev['total']} files[/cyan]")
                case "batch_file":
                    prog.update(
                        task,
                        description=f"[{ev['current']}/{ev['total']}] {ev['filename']}",
                        completed=0,
                    )
                case "file_error":
                    console.print(
                        f"[red]  ✗ {ev['filename']}: {ev['error']}[/red]"
                    )
                case "batch_completed":
                    console.print(
                        f"[bold green]✓ {ev['success']} succeeded, "
                        f"{ev['failed']} failed[/bold green]"
                    )
                case "info":
                    console.print(f"[dim]  {ev.get('message', '')}[/dim]")
                case "track_done":
                    console.print(f"[green]  ✓ {ev.get('message', '')}[/green]")
                case "track_skip":
                    console.print(
                        f"[yellow]  ⊘ {ev.get('message', '')}[/yellow]"
                    )

    console.print("[bold green]✓ Done![/bold green]")


# ── Root callback (→ TUI when no subcommand) ─────────────────

@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=_version_cb, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Launch interactive TUI when called without a subcommand."""
    if ctx.invoked_subcommand is None:
        from h1tool.interfaces.tui import run_tui

        run_tui()
        raise typer.Exit()


# ── download ─────────────────────────────────────────────────
@app.command()
def download(
    url: Annotated[str, typer.Option("-u", "--url", help="URL to download.")],
    audio_only: Annotated[
        bool, typer.Option("-a", "--audio", help="Extract audio only (MP3).")
    ] = False,
    resolution: Annotated[
        str, typer.Option("-r", "--resolution", help="480 / 720 / 1080 / 2160 / best")
    ] = "best",
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Output directory.")
    ] = _DEFAULT_DOWNLOADS,
    playlist: Annotated[
        bool, typer.Option("--playlist", help="Download the full playlist.")
    ] = False,
    fmt: Annotated[
        str, typer.Option("-f", "--format", help="Container format.")
    ] = "mp4",
) -> None:
    """Download video or audio from any URL (YouTube, TikTok, …)."""
    from h1tool.core.downloaders import download_audio, download_video
    from h1tool.core.exceptions import DownloadError
    from h1tool.utils.env_checker import check_ffmpeg, check_js_runtime, check_yt_dlp

    if not check_yt_dlp():
        _die("yt-dlp is not installed.", hint="pip install yt-dlp")

    js = check_js_runtime()
    if not js.available and js.warning:
        console.print(f"[yellow]⚠  {js.warning}[/yellow]")

    if audio_only and not check_ffmpeg():
        _die(
            "ffmpeg is required for audio extraction but was not found in PATH.",
            hint="https://ffmpeg.org/download.html",
        )

    try:
        if audio_only:
            gen = download_audio(url=url, output_dir=output, playlist=playlist)
            _consume(gen, "Downloading audio")
        else:
            gen = download_video(
                url=url,
                output_dir=output,
                resolution=resolution,
                format_ext=fmt,
                playlist=playlist,
            )
            _consume(gen, "Downloading video")
    except DownloadError as exc:
        _die(f"Download failed: {exc}", exc=exc)

# ── convert ──────────────────────────────────────────────────

@app.command()
def convert(
    input_path: Annotated[
        Path | None, typer.Option("-i", "--input", help="Input file.")
    ] = None,
    fmt: Annotated[str, typer.Option("-f", "--format", help="Target format.")] = ...,
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Output directory.")
    ] = _DEFAULT_CONVERTED,
    batch: Annotated[
        Path | None, typer.Option("--batch", help="Directory for batch conversion.")
    ] = None,
) -> None:
    """Convert media files locally (requires ffmpeg in PATH)."""
    from h1tool.core.converters import batch_convert, convert_file
    from h1tool.core.exceptions import ConversionError, FFmpegNotFoundError
    from h1tool.utils.env_checker import check_ffmpeg

    if not check_ffmpeg():
        _die(
            "ffmpeg not found in PATH.",
            hint="https://ffmpeg.org/download.html",
        )

    if batch is not None:
        gen = batch_convert(batch, fmt, output)
        label = f"Batch → {fmt.upper()}"
    elif input_path is not None:
        gen = convert_file(input_path, fmt, output)
        label = f"Converting → {fmt.upper()}"
    else:
        _die("Provide --input (-i) for a single file or --batch for a directory.")
        return

    try:
        _consume(gen, label)
    except (ConversionError, FFmpegNotFoundError) as exc:
        _die(f"Conversion failed: {exc}", exc=exc)


# ── spotify ──────────────────────────────────────────────────

@app.command()
def spotify(
    url: Annotated[str, typer.Option("-u", "--url", help="Spotify URL.")],
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Output directory.")
    ] = _DEFAULT_SPOTIFY,
    fmt: Annotated[
        str, typer.Option("-f", "--format", help="Audio format.")
    ] = "mp3",
) -> None:
    """Download tracks / albums / playlists from Spotify."""
    from h1tool.core.exceptions import SpotDLNotFoundError, SpotifyError
    from h1tool.core.spotify import download_spotify
    from h1tool.utils.env_checker import check_spotdl_config

    status = check_spotdl_config()
    if not status.available:
        _die("spotdl not found in PATH.", hint="pip install spotdl")

    if status.warning:
        console.print(f"[yellow]⚠  {status.warning}[/yellow]")

    try:
        gen = download_spotify(url, output, fmt)
        _consume(gen, "Spotify download")
    except (SpotifyError, SpotDLNotFoundError) as exc:
        _die(f"Spotify failed: {exc}", exc=exc)
