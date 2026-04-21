"""Tests for cronwrap.pause and cronwrap.pause_cli."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from cronwrap.pause import PauseConfig, PauseManager, PauseState
from cronwrap.pause_cli import build_parser, cmd_pause, cmd_resume, cmd_status


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_config(tmp_path):
    return PauseConfig(enabled=True, state_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# PauseConfig
# ---------------------------------------------------------------------------

def test_pause_config_enabled_by_default():
    cfg = PauseConfig()
    assert cfg.enabled is True


def test_pause_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_PAUSE_ENABLED", "false")
    monkeypatch.setenv("CRONWRAP_PAUSE_STATE_DIR", "/custom/dir")
    cfg = PauseConfig.from_env()
    assert cfg.enabled is False
    assert cfg.state_dir == "/custom/dir"


# ---------------------------------------------------------------------------
# PauseManager
# ---------------------------------------------------------------------------

def test_is_paused_false_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = PauseManager(tmp_config, "myjob")
    assert mgr.is_paused() is False


def test_is_paused_false_when_no_state(tmp_config):
    mgr = PauseManager(tmp_config, "myjob")
    assert mgr.is_paused() is False


def test_pause_creates_state_file(tmp_config, tmp_path):
    mgr = PauseManager(tmp_config, "myjob")
    state = mgr.pause(reason="maintenance")
    assert state.paused is True
    assert state.reason == "maintenance"
    path = tmp_path / "myjob.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["paused"] is True
    assert data["reason"] == "maintenance"


def test_is_paused_true_after_pause(tmp_config):
    mgr = PauseManager(tmp_config, "myjob")
    mgr.pause()
    assert mgr.is_paused() is True


def test_resume_clears_state(tmp_config):
    mgr = PauseManager(tmp_config, "myjob")
    mgr.pause()
    mgr.resume()
    assert mgr.is_paused() is False


def test_resume_noop_when_not_paused(tmp_config):
    mgr = PauseManager(tmp_config, "myjob")
    mgr.resume()  # should not raise


def test_status_returns_none_when_no_state(tmp_config):
    mgr = PauseManager(tmp_config, "myjob")
    assert mgr.status() is None


def test_status_returns_state_after_pause(tmp_config):
    mgr = PauseManager(tmp_config, "myjob")
    mgr.pause(reason="testing")
    state = mgr.status()
    assert state is not None
    assert state.paused is True
    assert state.reason == "testing"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_status_not_paused(tmp_config, capsys):
    mgr = PauseManager(tmp_config, "myjob")
    args = type("Args", (), {"job": "myjob"})()
    with patch("cronwrap.pause_cli._manager", return_value=mgr):
        cmd_status(args)
    out = capsys.readouterr().out
    assert "ACTIVE" in out


def test_cmd_pause_prints_confirmation(tmp_config, capsys):
    mgr = PauseManager(tmp_config, "myjob")
    args = type("Args", (), {"job": "myjob", "reason": "deploy"}) ()
    with patch("cronwrap.pause_cli._manager", return_value=mgr):
        cmd_pause(args)
    out = capsys.readouterr().out
    assert "paused" in out.lower()


def test_cmd_resume_confirms(tmp_config, capsys):
    mgr = PauseManager(tmp_config, "myjob")
    mgr.pause()
    args = type("Args", (), {"job": "myjob"})()
    with patch("cronwrap.pause_cli._manager", return_value=mgr):
        cmd_resume(args)
    out = capsys.readouterr().out
    assert "resumed" in out.lower()
