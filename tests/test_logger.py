"""Tests for utils/logger.py — file logging."""

from pathlib import Path

from h1tool.utils.logger import get_log_dir, log_error


def test_log_error_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("h1tool.utils.logger._LOG_DIR", tmp_path)

    exc = ValueError("test boom")
    path = log_error(exc, context="unit_test", log_file="test.log")

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "ValueError" in content
    assert "test boom" in content
    assert "unit_test" in content


def test_log_error_appends(tmp_path, monkeypatch):
    monkeypatch.setattr("h1tool.utils.logger._LOG_DIR", tmp_path)

    log_error(RuntimeError("first"), log_file="multi.log")
    log_error(RuntimeError("second"), log_file="multi.log")

    content = (tmp_path / "multi.log").read_text(encoding="utf-8")
    assert content.count("RuntimeError") == 2


def test_get_log_dir(tmp_path, monkeypatch):
    target = tmp_path / "custom_logs"
    monkeypatch.setattr("h1tool.utils.logger._LOG_DIR", target)

    result = get_log_dir()
    assert result == target
    assert result.is_dir()