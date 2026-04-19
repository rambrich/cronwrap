"""Tests for cronwrap.replay."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwrap.deadletter import DeadLetterConfig, DeadLetterEntry
from cronwrap.replay import ReplayConfig, ReplayManager
from cronwrap.runner import RunResult


def _entry(id: str, command: str = "echo hi", failure_count: int = 1) -> DeadLetterEntry:
    return DeadLetterEntry(id=id, command=command, failure_count=failure_count, timestamp=0.0)


def _result(success: bool = True) -> RunResult:
    return RunResult(success=success, exit_code=0 if success else 1, stdout="", stderr="", duration=0.1)


def test_replay_config_disabled_by_default():
    cfg = ReplayConfig()
    assert cfg.enabled is False


def test_replay_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_REPLAY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_REPLAY_MAX", "5")
    cfg = ReplayConfig.from_env()
    assert cfg.enabled is True
    assert cfg.max_replays == 5


def test_replay_all_returns_empty_when_disabled():
    mgr = ReplayManager(ReplayConfig(enabled=False))
    result = mgr.replay_all()
    assert result.replayed == 0


def test_replay_all_replays_entries():
    cfg = ReplayConfig(enabled=True, max_replays=10)
    mgr = ReplayManager(cfg)
    mgr.dl_manager = MagicMock()
    mgr.dl_manager.list.return_value = [_entry("a"), _entry("b")]
    mgr.dl_manager.remove = MagicMock()

    with patch("cronwrap.replay.run_command", return_value=_result(True)):
        result = mgr.replay_all()

    assert result.replayed == 2
    assert result.succeeded == 2
    assert result.failed == 0
    assert mgr.dl_manager.remove.call_count == 2


def test_replay_all_respects_max():
    cfg = ReplayConfig(enabled=True, max_replays=1)
    mgr = ReplayManager(cfg)
    mgr.dl_manager = MagicMock()
    mgr.dl_manager.list.return_value = [_entry("a"), _entry("b"), _entry("c")]
    mgr.dl_manager.remove = MagicMock()

    with patch("cronwrap.replay.run_command", return_value=_result(True)):
        result = mgr.replay_all()

    assert result.replayed == 1
    assert result.skipped == 2


def test_replay_one_returns_none_when_disabled():
    mgr = ReplayManager(ReplayConfig(enabled=False))
    mgr.dl_manager = MagicMock()
    assert mgr.replay_one("x") is None


def test_replay_one_runs_matching_entry():
    cfg = ReplayConfig(enabled=True)
    mgr = ReplayManager(cfg)
    mgr.dl_manager = MagicMock()
    mgr.dl_manager.list.return_value = [_entry("abc", command="ls")]
    mgr.dl_manager.remove = MagicMock()

    with patch("cronwrap.replay.run_command", return_value=_result(True)) as mock_run:
        run = mgr.replay_one("abc")

    mock_run.assert_called_once_with("ls")
    assert run is not None
    assert run.success is True
