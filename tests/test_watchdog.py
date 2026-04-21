"""Tests for cronwrap.watchdog."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.runner import RunResult
from cronwrap.watchdog import WatchdogConfig, WatchdogManager, WatchdogState


def _result(success: bool = True) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=0 if success else 1,
        stdout="hi",
        stderr="",
        duration=0.1,
        success=success,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return WatchdogConfig(
        enabled=True,
        interval_seconds=60,
        state_dir=str(tmp_path),
        job_name="test-job",
    )


def test_watchdog_config_disabled_by_default():
    cfg = WatchdogConfig()
    assert cfg.enabled is False


def test_watchdog_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_WATCHDOG_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_WATCHDOG_INTERVAL", "120")
    monkeypatch.setenv("CRONWRAP_JOB_NAME", "my-job")
    cfg = WatchdogConfig.from_env()
    assert cfg.enabled is True
    assert cfg.interval_seconds == 120
    assert cfg.job_name == "my-job"


def test_record_returns_none_when_disabled(tmp_path):
    cfg = WatchdogConfig(enabled=False, state_dir=str(tmp_path), job_name="j")
    mgr = WatchdogManager(cfg)
    assert mgr.record(_result()) is None


def test_record_returns_none_on_failure(tmp_config):
    mgr = WatchdogManager(tmp_config)
    assert mgr.record(_result(success=False)) is None


def test_record_writes_state(tmp_config):
    mgr = WatchdogManager(tmp_config)
    state = mgr.record(_result())
    assert state is not None
    assert state.job_name == "test-job"
    p = mgr._state_path()
    assert p.exists()
    data = json.loads(p.read_text())
    assert "last_run_at" in data


def test_is_overdue_false_when_disabled(tmp_path):
    cfg = WatchdogConfig(enabled=False, state_dir=str(tmp_path), job_name="j")
    mgr = WatchdogManager(cfg)
    assert mgr.is_overdue() is False


def test_is_overdue_false_when_no_state(tmp_config):
    mgr = WatchdogManager(tmp_config)
    assert mgr.is_overdue() is False


def test_is_overdue_false_when_recent(tmp_config):
    mgr = WatchdogManager(tmp_config)
    mgr.record(_result())
    assert mgr.is_overdue() is False


def test_is_overdue_true_when_stale(tmp_config, tmp_path):
    mgr = WatchdogManager(tmp_config)
    # Write a state with a very old timestamp
    old_state = WatchdogState(last_run_at=time.time() - 9999, job_name="test-job")
    p = mgr._state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(old_state.to_dict()))
    assert mgr.is_overdue() is True


def test_reset_removes_state(tmp_config):
    mgr = WatchdogManager(tmp_config)
    mgr.record(_result())
    assert mgr._state_path().exists()
    mgr.reset()
    assert not mgr._state_path().exists()
