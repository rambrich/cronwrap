"""Tests for cronwrap.trend."""
import json
from pathlib import Path

import pytest

from cronwrap.runner import RunResult
from cronwrap.trend import TrendConfig, TrendManager


def _result(rc: int = 0) -> RunResult:
    return RunResult(returncode=rc, stdout="", stderr="", duration=1.0, timed_out=False)


@pytest.fixture
def tmp_config(tmp_path):
    return TrendConfig(enabled=True, window=5, state_dir=str(tmp_path / "trend"))


# ── config ────────────────────────────────────────────────────────────────────

def test_trend_config_disabled_by_default():
    cfg = TrendConfig()
    assert cfg.enabled is False


def test_trend_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_TREND_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_TREND_WINDOW", "10")
    cfg = TrendConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 10


def test_trend_config_window_clamped(monkeypatch):
    monkeypatch.setenv("CRONWRAP_TREND_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_TREND_WINDOW", "1")
    cfg = TrendConfig.from_env()
    assert cfg.window == 2


# ── record ────────────────────────────────────────────────────────────────────

def test_record_returns_none_when_disabled(tmp_path):
    cfg = TrendConfig(enabled=False, state_dir=str(tmp_path))
    mgr = TrendManager(config=cfg)
    assert mgr.record("myjob", _result(0)) is None


def test_record_returns_result(tmp_config):
    mgr = TrendManager(config=tmp_config)
    res = mgr.record("myjob", _result(0))
    assert res is not None
    assert res.job == "myjob"
    assert res.success_rate == 1.0
    assert res.total_runs == 1


def test_record_tracks_failures(tmp_config):
    mgr = TrendManager(config=tmp_config)
    for _ in range(4):
        mgr.record("job", _result(0))
    res = mgr.record("job", _result(1))  # 1 failure in last 5
    assert res.success_rate == pytest.approx(0.8)


def test_record_detects_degrading(tmp_config):
    mgr = TrendManager(config=tmp_config)
    for _ in range(5):
        mgr.record("job", _result(1))   # all failures
    res = mgr.record("job", _result(1))
    assert res.is_degrading is True


def test_record_detects_recovering(tmp_config):
    mgr = TrendManager(config=tmp_config)
    # first window: all failures
    for _ in range(5):
        mgr.record("job", _result(1))
    # second window: mostly successes
    for _ in range(5):
        mgr.record("job", _result(0))
    res = mgr.record("job", _result(0))
    assert res.is_recovering is True


# ── reset ─────────────────────────────────────────────────────────────────────

def test_reset_removes_state(tmp_config):
    mgr = TrendManager(config=tmp_config)
    mgr.record("job", _result(0))
    state_file = Path(tmp_config.state_dir) / "job.json"
    assert state_file.exists()
    mgr.reset("job")
    assert not state_file.exists()


def test_reset_noop_when_no_state(tmp_config):
    mgr = TrendManager(config=tmp_config)
    mgr.reset("nonexistent")  # should not raise
