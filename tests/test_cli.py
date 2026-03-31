"""Smoke tests for CLI — invokes typer app via CliRunner."""

from typer.testing import CliRunner

from h1tool.interfaces.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "h1tool" in result.output
    assert "2.0" in result.output


def test_help_flag():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "download" in result.output
    assert "convert" in result.output
    assert "spotify" in result.output


def test_download_help():
    result = runner.invoke(app, ["download", "--help"])
    assert result.exit_code == 0
    assert "--url" in result.output
    assert "--audio" in result.output


def test_convert_help():
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--batch" in result.output


def test_spotify_help():
    result = runner.invoke(app, ["spotify", "--help"])
    assert result.exit_code == 0
    assert "--url" in result.output


def test_download_missing_url():
    result = runner.invoke(app, ["download"])
    assert result.exit_code != 0


def test_convert_missing_format():
    result = runner.invoke(app, ["convert"])
    assert result.exit_code != 0


def test_spotify_missing_url():
    result = runner.invoke(app, ["spotify"])
    assert result.exit_code != 0