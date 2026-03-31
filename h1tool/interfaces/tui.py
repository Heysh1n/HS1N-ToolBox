"""Interactive TUI — Rich-based terminal UI.

Launched automatically when ``h1tool`` is called without arguments.
All user interaction lives here; core is called as generators.
Every caught error is persisted via logger.
"""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table

from h1tool import __version__
from h1tool.core.exceptions import (
    ConversionError,
    DownloadError,
    FFmpegNotFoundError,
    SpotDLNotFoundError,
    SpotifyError,
)
from h1tool.utils.logger import log_error

console = Console()

_LOGO = (
    "[bright_white]██╗  ██╗███████╗ ██╗███╗   ██╗[/]\n"
    "[white]██║  ██║██╔════╝███║████╗  ██║[/]\n"
    "[magenta]███████║███████╗╚██║██╔██╗ ██║[/]\n"
    "[bright_magenta]██╔══██║╚════██║ ██║██║╚██╗██║[/]\n"
    "[magenta]██║  ██║███████║ ██║██║ ╚████║[/]\n"
    "[dim magenta]╚═╝  ╚═╝╚══════╝ ╚═╝╚═╝  ╚═══╝[/]"
)


def _header(subtitle: str | None = None) -> None:
    console.clear()
    console.print()
    title = f"HS1N-ToolBox  v{__version__}"
    body = _LOGO
    if subtitle:
        body += f"\n\n[bold]{subtitle}[/bold]"
    console.print(Panel(body, title=title, border_style="magenta", padding=(1, 4)))
    console.print()


def _pause() -> None:
    console.print()
    Prompt.ask("[dim]Press Enter to continue…[/dim]", default="")


def _error(msg: str, *, hint: str | None = None, exc: Exception | None = None) -> None:
    console.print(f"\n[bold red]✗ {msg}[/bold red]")
    if hint:
        console.print(f"[dim]  ↳ {hint}[/dim]")
    if exc:
        path = log_error(exc, context=msg)
        console.print(f"[dim]  📝 logged → {path}[/dim]")


def _env_ok(name: str, check_fn, hint: str) -> bool:
    if check_fn():
        return True
    _error(f"{name} not found in PATH.", hint=hint)
    _pause()
    return False

def _show_status(status) -> None:
    """Print ToolStatus warning + hints if any."""
    if status.warning:
        console.print(f"[yellow]⚠  {status.warning}[/yellow]")
    for h in getattr(status, "hints", []):
        console.print(f"[dim]   {h}[/dim]")
    if status.warning:
        console.print()


def _ask(label: str, **kw) -> str:
    return Prompt.ask(label, **kw).strip().strip("'\"")


def _consume(gen, label: str) -> None:
    """Drain a core generator, painting a Rich progress bar."""
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
                    prog.update(
                        task, completed=100, description=f"{label} · merging"
                    )
                case "completed":
                    prog.update(task, completed=100)
                    if out := ev.get("output"):
                        console.print(f"[green]  → {out}[/green]")
                case "batch_started":
                    console.print(f"[cyan]Found {ev['total']} file(s)[/cyan]")
                case "batch_file":
                    prog.update(
                        task,
                        description=(
                            f"[{ev['current']}/{ev['total']}] {ev['filename']}"
                        ),
                        completed=0,
                    )
                case "file_error":
                    console.print(
                        f"[red]  ✗ {ev['filename']}: {ev['error']}[/red]"
                    )
                case "batch_completed":
                    console.print(
                        f"\n[bold green]✓ {ev['success']} succeeded, "
                        f"{ev['failed']} failed[/bold green]"
                    )
                case "info":
                    console.print(f"[dim]  {ev.get('message', '')}[/dim]")
                case "track_done":
                    console.print(
                        f"[green]  ✓ {ev.get('message', '')}[/green]"
                    )
                case "track_skip":
                    console.print(
                        f"[yellow]  ⊘ {ev.get('message', '')}[/yellow]"
                    )

    console.print("[bold green]✓ Done![/bold green]")


def _download_menu() -> None:
    _header("📥 Download Video / Audio")

    from h1tool.utils.env_checker import (
        check_cookies_file,
        check_ffmpeg,
        check_js_runtime,
        check_yt_dlp,
        check_yt_dlp_version,
    )

    if not _env_ok("yt-dlp", check_yt_dlp, "pip install yt-dlp"):
        return

    # Show non-fatal warnings
    for status in (check_js_runtime(), check_yt_dlp_version(), check_cookies_file()):
        if not status.available or status.warning:
            _show_status(status)

    url = _ask("[bold]URL[/bold]")
    if not url:
        _error("URL cannot be empty.")
        _pause()
        return

    audio_only = Confirm.ask("Audio only (MP3)?", default=False)

    resolution = "best"
    fmt = "mp4"
    if not audio_only:
        resolution = _ask(
            "Resolution [dim](480 / 720 / 1080 / 2160 / best)[/dim]",
            default="best",
        )

    output = Path(_ask("Output directory", default="downloads"))
    playlist = Confirm.ask("Download full playlist?", default=False)

    if audio_only and not _env_ok("ffmpeg", check_ffmpeg, "https://ffmpeg.org"):
        return

    from h1tool.core.downloaders import download_audio, download_video

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
        _error(f"Download failed: {exc}", exc=exc)

    _pause()


def _spotify_menu() -> None:
    _header("🎧 Spotify Download")

    from h1tool.utils.env_checker import check_spotdl_config

    status = check_spotdl_config()
    if not status.available:
        _error("spotdl not found.", hint="pip install spotdl")
        _pause()
        return

    _show_status(status)

    if status.warning and not Confirm.ask("Continue anyway?", default=True):
        return

    console.print("[dim]VPN may be required in some regions.[/dim]\n")

    url = _ask("[bold]Spotify URL[/bold]")
    if not url:
        _error("URL cannot be empty.")
        _pause()
        return

    fmt = _ask("Audio format", default="mp3")
    output = Path(_ask("Output directory", default="downloads/spotify"))

    from h1tool.core.spotify import download_spotify

    try:
        gen = download_spotify(url, output, fmt)
        _consume(gen, "Spotify download")
    except (SpotifyError, SpotDLNotFoundError) as exc:
        _error(f"Spotify failed: {exc}", exc=exc)

    _pause()



def _convert_menu() -> None:
    _header("♻️  Convert Media")

    mode = Prompt.ask(
        "[bold]Mode[/bold]  [dim][1] single file  [2] batch directory[/dim]",
        choices=["1", "2"],
        default="1",
    )

    fmt = _ask(
        "[bold]Target format[/bold] [dim](mp4, mp3, wav, png, …)[/dim]"
    )
    if not fmt:
        _error("Format cannot be empty.")
        _pause()
        return

    output = Path(_ask("Output directory", default="converted"))

    from h1tool.utils.env_checker import check_ffmpeg

    if not _env_ok("ffmpeg", check_ffmpeg, "https://ffmpeg.org"):
        return

    from h1tool.core.converters import batch_convert, convert_file

    try:
        if mode == "1":
            path_str = _ask("[bold]Input file[/bold]")
            if not path_str:
                _error("Path cannot be empty.")
                _pause()
                return
            gen = convert_file(Path(path_str), fmt, output)
            _consume(gen, f"Converting → {fmt.upper()}")
        else:
            dir_str = _ask("[bold]Input directory[/bold]")
            if not dir_str:
                _error("Path cannot be empty.")
                _pause()
                return
            gen = batch_convert(Path(dir_str), fmt, output)
            _consume(gen, f"Batch → {fmt.upper()}")
    except (ConversionError, FFmpegNotFoundError) as exc:
        _error(f"Conversion failed: {exc}", exc=exc)

    _pause()


def _download_menu() -> None:
    _header("📥 Download Video / Audio")

    # ── env checks with warnings ──
    from h1tool.utils.env_checker import check_ffmpeg, check_js_runtime, check_yt_dlp

    if not _env_ok("yt-dlp", check_yt_dlp, "pip install yt-dlp"):
        return

    js = check_js_runtime()
    if not js.available and js.warning:
        console.print(f"[yellow]⚠  {js.warning}[/yellow]\n")

    url = _ask("[bold]URL[/bold]")
    if not url:
        _error("URL cannot be empty.")
        _pause()
        return

    audio_only = Confirm.ask("Audio only (MP3)?", default=False)

    resolution = "best"
    fmt = "mp4"
    if not audio_only:
        resolution = _ask(
            "Resolution [dim](480 / 720 / 1080 / 2160 / best)[/dim]",
            default="best",
        )

    output = Path(_ask("Output directory", default="downloads"))
    playlist = Confirm.ask("Download full playlist?", default=False)

    if audio_only and not _env_ok("ffmpeg", check_ffmpeg, "https://ffmpeg.org"):
        return

    from h1tool.core.downloaders import download_audio, download_video

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
        _error(f"Download failed: {exc}", exc=exc)

    _pause()



def _mp3_menu() -> None:
    _header("🎞️  Convert to MP3")

    path_str = _ask("[bold]Input file or directory[/bold]")
    if not path_str:
        _error("Path cannot be empty.")
        _pause()
        return

    output = Path(_ask("Output directory", default="converted"))

    from h1tool.utils.env_checker import check_ffmpeg

    if not _env_ok("ffmpeg", check_ffmpeg, "https://ffmpeg.org"):
        return

    from h1tool.core.converters import convert_to_mp3

    try:
        gen = convert_to_mp3(Path(path_str), output)
        _consume(gen, "Converting → MP3")
    except (ConversionError, FFmpegNotFoundError) as exc:
        _error(f"Conversion failed: {exc}", exc=exc)

    _pause()


def run_tui() -> None:
    """Entry-point for interactive TUI mode."""
    while True:
        _header()

        table = Table(
            box=box.ROUNDED,
            border_style="magenta",
            show_header=False,
            padding=(0, 2),
        )
        table.add_column("", style="bold", width=3, justify="center")
        table.add_column("")
        table.add_row("1", "📥  Download Video / Audio")
        table.add_row("2", "♻️   Convert Media")
        table.add_row("3", "🎧  Spotify Download")
        table.add_row("4", "🎞️   Convert All to MP3")
        table.add_row("0", "🚪  Exit")
        console.print(table)
        console.print()

        try:
            choice = Prompt.ask(
                "[bold]Select[/bold]",
                choices=["0", "1", "2", "3", "4"],
                default="0",
            )
        except KeyboardInterrupt:
            break

        try:
            match choice:
                case "1":
                    _download_menu()
                case "2":
                    _convert_menu()
                case "3":
                    _spotify_menu()
                case "4":
                    _mp3_menu()
                case "0":
                    console.clear()
                    console.print(
                        Panel(
                            "[bold]Thank you for using HS1N-Toolbox! 👋[/bold]",
                            border_style="magenta",
                        )
                    )
                    return
        except KeyboardInterrupt:
            continue
