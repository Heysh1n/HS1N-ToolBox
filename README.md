# 🎬🎵 HS1N-Toolbox

Universal media Swiss Army knife. Download from 1000+ platforms (YouTube, Spotify, TikTok…) and convert video/audio/images locally.

Features two modes: a lightning-fast **CLI** for scripts and a beautiful interactive **TUI** for terminal lovers.

[![CI](https://github.com/Heysh1n/HS1N-Toolbox/actions/workflows/ci.yml/badge.svg)](https://github.com/Heysh1n/HS1N-Toolbox/actions)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## 📦 Features

| Feature | Details |
|---------|---------|
| **Universal Downloader** | Video, audio, playlists via URL (powered by `yt-dlp`) |
| **Spotify Support** | Tracks, albums, playlists (via `spotdl`) |
| **Media Converter** | Batch convert 20+ formats locally (requires `ffmpeg`) |
| **Dual Interface** | Argument-driven **CLI** or fully interactive **TUI** |
| **Standalone Binary** | No Python or `pip` needed for end users |
| **Cross-platform** | Windows, Linux, macOS |

---

## 🚀 Installation

### Option A — Pre-built binary (recommended)

1. Go to the [Releases](https://github.com/Heysh1n/HS1N-Toolbox/releases) page.
2. Download the binary for your OS.
3. *(Optional)* Add it to your system `PATH` to use `h1tool` from anywhere.

### Option B — From source

```bash
git clone https://github.com/Heysh1n/HS1N-Toolbox.git
cd HS1N-Toolbox
make setup
```

> **Note:** For media conversion, [FFmpeg](https://ffmpeg.org/download.html) must be installed and in your `PATH`.

---

## 🎮 TUI Mode (Interactive)

Run without any arguments to launch the interactive menu:

```bash
h1tool
```

Navigate with your keyboard — download, convert, and monitor progress in real-time.

---

## 💻 CLI Mode

### Download

```bash
# Video (best quality)
h1tool download -u "https://youtube.com/watch?v=..."

# Audio only (MP3)
h1tool download -u "https://youtube.com/watch?v=..." -a

# Custom resolution + playlist
h1tool download -u "https://youtube.com/playlist?list=..." -r 1080 --playlist

# Custom output directory
h1tool download -u "URL" -o ~/Videos
```

### Convert

```bash
# Single file
h1tool convert -i "video.mkv" -f mp4

# Batch convert directory
h1tool convert --batch "./raw_videos" -f mp4 -o "./converted"
```

### Spotify

```bash
h1tool spotify -u "https://open.spotify.com/track/..."
h1tool spotify -u "https://open.spotify.com/album/..." -f m4a
```

### Other

```bash
h1tool --version
h1tool --help
h1tool download --help
```

---

## 🏗️ Architecture

```
h1tool/
├── core/               # 🔇 Silent core — NO print, NO UI
│   ├── downloaders.py  #    yield progress dicts, raise on error
│   ├── converters.py   #    yield progress dicts, raise on error
│   ├── spotify.py      #    yield progress dicts, raise on error
│   └── exceptions.py   #    custom exception hierarchy
├── interfaces/         # 🎨 Presentation layer — ALL UI here
│   ├── cli.py          #    Typer commands + Rich progress
│   └── tui.py          #    Interactive menus + Rich prompts
└── utils/
    ├── env_checker.py   #    shutil.which checks (no install attempts)
    └── logger.py        #    File-based error logging
```

**Key rules:**
- Core never imports `print`, `Rich`, `Typer`, or any UI code.
- Core communicates progress via `yield {"status": "...", "percent": ...}`.
- Core communicates errors via `raise CustomError(...)`.
- Only `interfaces/` consumes generators and draws the UI.

---

## 🛠️ Development

```bash
make setup          # Create venv, install editable + dev deps
make run            # Run TUI mode
make run ARGS="download -u 'URL' -a"   # Run CLI mode
make lint           # Ruff lint
make test           # Pytest
make build          # PyInstaller → dist/h1tool
make clean          # Remove venv, dist, caches
```

### Running tests

```bash
make test
# or directly:
pytest tests/ -v
```

---

## 📁 Logs

Errors are logged to `~/.h1tool/logs/h1tool.log` automatically. Check this file for detailed tracebacks when something goes wrong.

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

**Author:** [Heysh1n](https://github.com/Heysh1n)

<p align="center">
  Made with ❤️ by Heysh1n
</p>
