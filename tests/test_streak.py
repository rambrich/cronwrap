"""Tests for cronwrap.streak."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.runner import RunResult
from cronwrap.streak import StreakConfig, StreakManager, StreakState


def _result(rc: int) -> RunResult:
    return RunResult(command="echo hi", returncode=rc, stdout="", stderr="", duration=0.1)


@pytest.fixture()
def tmp_config(tmp_path):
    return StreakConfig(enabled=True, state_dir=str(tmp_path), alert_on_failure_streak=3)


def test_streak_config_disabled_by_default():
    cfg = StreakConfig()
    assert cfg.enabled is False


def test_streak_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_STREAK_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_STREAK_FAILURE_ALERT", "5")
    monkeypatch.setenv("CRONWRAP_STREAK_SUCCESS_ALERT", "2")
    cfg = StreakConfig.from_env()
    assert cfg.enabled is True
    assert cfg.alert_on_failure_streak == 5
    assert cfg.alert_on_success_streak == 2


def test_record_returns_none_when_disabled(tmp_path):
    cfg = StreakConfig(enabled=False, state_dir=str(tmp_path))
    mgr = StreakManager(cfg, "myjob")
    assert mgr.record(_result(1)) is None


def test_record_success_increments_successes(tmp_config):
    mgr = StreakManager(tmp_config, "myjob")
    res = mgr.record(_result(0))
    assert res is not None
    assert res.state.consecutive_successes == 1
    assert res.state.consecutive_failures == 0
    assert res.state.last_status == "success"


def test_record_failure_increments_failures(tmp_config):
    mgr = StreakManager(tmp_config, "myjob")
    res = mgr.record(_result(1))
    assert res is not None
    assert res.state.consecutive_failures == 1
    assert res.state.consecutive_successes == 0
    assert res.state.last_status == "failure"


def test_success_resets_failure_count(tmp_config):
    mgr = StreakManager(tmp_config, "myjob")
    mgr.record(_result(1))
    mgr.record(_result(1))
    res = mgr.record(_result(0))
    assert res.state.consecutive_failures == 0
    assert res.state.consecutive_successes == 1


def test_failure_alert_triggered(tmp_config):
    mgr = StreakManager(tmp_config, "myjob")
    mgr.record(_result(1))
    mgr.record(_result(1))
    res = mgr.record(_result(1))
    assert res.failure_alert is True


def test_failure_alert_not_triggered_below_threshold(tmp_config):
    mgr = StreakManager(tmp_config, "myjob")
    mgr.record(_result(1))
    res = mgr.record(_result(1))
    assert res.failure_alert is False


def test_success_alert_triggered(tmp_path):
    cfg = StreakConfig(enabled=True, state_dir=str(tmp_path), alert_on_success_streak=2)
    mgr = StreakManager(cfg, "myjob")
    mgr.record(_result(0))
    res = mgr.record(_result(0))
    assert res.success_alert is True


def test_reset_removes_state_file(tmp_config, tmp_path):
    mgr = StreakManager(tmp_config, "myjob")
    mgr.record(_result(0))
    state_files = list(Path(str(tmp_path)).glob("*.json"))
    assert len(state_files) == 1
    mgr.reset()
    state_files = list(Path(str(tmp_path)).glob("*.json"))
    assert len(state_files) == 0


def test_state_persists_across_instances(tmp_config):
    mgr1 = StreakManager(tmp_config, "myjob")
    mgr1.record(_result(1))
    mgr1.record(_result(1))
    mgr2 = StreakManager(tmp_config, "myjob")
    res = mgr2.record(_result(1))
    assert res.state.consecutive_failures == 3
