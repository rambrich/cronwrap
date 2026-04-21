"""Tests for cronwrap.window and cronwrap.window_cli."""
from __future__ import annotations

import sys
from datetime import time
from unittest.mock import patch

import pytest

from cronwrap.window import OutsideWindowError, WindowConfig, WindowManager
from cronwrap.window_cli import build_parser, cmd_check, cmd_status


# ---------------------------------------------------------------------------
# WindowConfig
# ---------------------------------------------------------------------------

def test_window_config_disabled_by_default():
    config = WindowConfig.from_env()
    assert config.enabled is False
    assert config.windows == []


def test_window_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_WINDOW_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_WINDOW_RANGES", "08:00-18:00")
    monkeypatch.setenv("CRONWRAP_WINDOW_TZ", "Europe/London")
    config = WindowConfig.from_env()
    assert config.enabled is True
    assert len(config.windows) == 1
    assert config.windows[0] == (time(8, 0), time(18, 0))
    assert config.timezone == "Europe/London"


def test_window_config_multiple_ranges(monkeypatch):
    monkeypatch.setenv("CRONWRAP_WINDOW_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_WINDOW_RANGES", "06:00-12:00,20:00-23:00")
    config = WindowConfig.from_env()
    assert len(config.windows) == 2


def test_window_config_ignores_bad_range(monkeypatch):
    monkeypatch.setenv("CRONWRAP_WINDOW_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_WINDOW_RANGES", "bad-range,08:00-09:00")
    config = WindowConfig.from_env()
    assert len(config.windows) == 1


# ---------------------------------------------------------------------------
# WindowManager.is_allowed
# ---------------------------------------------------------------------------

def _manager(ranges: str) -> WindowManager:
    config = WindowConfig(
        enabled=True,
        windows=[
            (time.fromisoformat(s), time.fromisoformat(e))
            for part in ranges.split(",")
            for s, e in [part.split("-")]
        ],
    )
    return WindowManager(config)


def test_is_allowed_when_disabled():
    mgr = WindowManager(WindowConfig(enabled=False))
    assert mgr.is_allowed(time(3, 0)) is True


def test_is_allowed_inside_window():
    mgr = _manager("08:00-18:00")
    assert mgr.is_allowed(time(12, 0)) is True


def test_is_blocked_outside_window():
    mgr = _manager("08:00-18:00")
    assert mgr.is_allowed(time(20, 0)) is False


def test_is_allowed_overnight_window():
    mgr = _manager("22:00-06:00")
    assert mgr.is_allowed(time(23, 0)) is True
    assert mgr.is_allowed(time(2, 0)) is True
    assert mgr.is_allowed(time(12, 0)) is False


def test_check_raises_outside_window():
    mgr = _manager("08:00-18:00")
    with pytest.raises(OutsideWindowError):
        mgr.check(time(20, 0))


def test_check_passes_inside_window():
    mgr = _manager("08:00-18:00")
    mgr.check(time(10, 0))  # should not raise


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_status_output(capsys):
    config = WindowConfig(
        enabled=True,
        windows=[(time(8, 0), time(18, 0))],
        timezone="UTC",
    )
    cmd_status(config)
    out = capsys.readouterr().out
    assert "enabled" in out
    assert "08:00:00-18:00:00" in out


def test_cmd_check_allowed(capsys):
    config = WindowConfig(enabled=True, windows=[(time(8, 0), time(18, 0))])
    cmd_check(config, "10:00")
    out = capsys.readouterr().out
    assert "ALLOWED" in out


def test_cmd_check_blocked_exits(capsys):
    config = WindowConfig(enabled=True, windows=[(time(8, 0), time(18, 0))])
    with pytest.raises(SystemExit) as exc:
        cmd_check(config, "20:00")
    assert exc.value.code == 1


def test_cmd_check_invalid_time_exits(capsys):
    config = WindowConfig(enabled=True, windows=[(time(8, 0), time(18, 0))])
    with pytest.raises(SystemExit) as exc:
        cmd_check(config, "not-a-time")
    assert exc.value.code == 2
