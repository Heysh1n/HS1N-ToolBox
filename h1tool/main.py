"""Application router. Delegates everything to the Typer CLI app."""

from h1tool.interfaces.cli import app


def run() -> None:
    app()


if __name__ == "__main__":
    run()
