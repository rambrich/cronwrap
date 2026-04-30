"""Tests for cronwrap.throughput."""
from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest

from cronwrap.runner import RunResult
from cronwrap.throughput import ThroughputConfig, ThroughputManager, ThroughputResult


def _result(success: bool = True, duration: float = 1.0) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=0 if success else 1,
        stdout="hi",
        stderr="",
        duration=duration,
        success=success,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return ThroughputConfig(
        enabled=True,
        window_seconds=3600,
        min_runs=3,
        state_dir=str(tmp_path),
    )


def test_throughput_config_disabled_by_default():
    cfg = ThroughputConfig()
    assert cfg.enabled is False


def test_throughput_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_THROUGHPUT_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_THROUGHPUT_WINDOW_SECONDS", "1800")
    monkeypatch.setenv("CRONWRAP_THROUGHPUT_MIN_RUNS", "5")
    cfg = ThroughputConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 1800
    assert cfg.min_runs == 5


def test_throughput_config_invalid_window_defaults(monkeypatch):
    monkeypatch.setenv("CRONWRAP_THROUGHPUT_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_THROUGHPUT_WINDOW_SECONDS", "bad")
    cfg = ThroughputConfig.from_env()
    assert cfg.window_seconds == 3600


def test_record_returns_none_when_disabled(tmp_path):
    cfg = ThroughputConfig(enabled=False, state_dir=str(tmp_path))
    mgr = ThroughputManager(cfg, "myjob")
    assert mgr.record(_result()) is None


def test_record_returns_result(tmp_config):
    mgr = ThroughputManager(tmp_config, "myjob")
    res = mgr.record(_result())
    assert isinstance(res, ThroughputResult)
    assert res.runs_in_window == 1
    assert res.job == "myjob"


def test_record_accumulates_runs(tmp_config):
    mgr = ThroughputManager(tmp_config, "myjob")
    mgr.record(_result())
    mgr.record(_result())
    res = mgr.record(_result())
    assert res.runs_in_window == 3
    assert res.below_threshold is False


def test_record_below_threshold(tmp_config):
    mgr = ThroughputManager(tmp_config, "myjob")
    res = mgr.record(_result())
    assert res.below_threshold is True


def test_record_prunes_old_timestamps(tmp_config, tmp_path):
    mgr = ThroughputManager(tmp_config, "myjob")
    old_ts = [time.time() - 7200]  # older than window
    state_file = mgr._state_path()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(old_ts))
    res = mgr.record(_result())
    assert res.runs_in_window == 1


def test_to_dict_keys(tmp_config):
    mgr = ThroughputManager(tmp_config, "myjob")
    res = mgr.record(_result())
    d = res.to_dict()
    assert set(d.keys()) == {"job", "runs_in_window", "window_seconds", "min_runs", "below_threshold"}
