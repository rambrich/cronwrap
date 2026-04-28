"""Tests for cronwrap.capacity."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch

from cronwrap.runner import RunResult
from cronwrap.capacity import CapacityConfig, CapacityManager, CapacityResult


def _result(duration: float = 1.0, exit_code: int = 0) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout="", stderr="", duration=duration, attempts=1)


@pytest.fixture
def tmp_config(tmp_path):
    return CapacityConfig(enabled=True, state_dir=str(tmp_path), window=5, warn_threshold=0.80)


def test_capacity_config_disabled_by_default():
    cfg = CapacityConfig()
    assert cfg.enabled is False


def test_capacity_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_CAPACITY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_CAPACITY_WINDOW", "10")
    monkeypatch.setenv("CRONWRAP_CAPACITY_WARN_THRESHOLD", "0.90")
    cfg = CapacityConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 10
    assert cfg.warn_threshold == pytest.approx(0.90)


def test_capacity_config_invalid_window_defaults(monkeypatch):
    monkeypatch.setenv("CRONWRAP_CAPACITY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_CAPACITY_WINDOW", "bad")
    cfg = CapacityConfig.from_env()
    assert cfg.window == 20


def test_capacity_config_window_clamped_to_minimum(monkeypatch):
    monkeypatch.setenv("CRONWRAP_CAPACITY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_CAPACITY_WINDOW", "1")
    cfg = CapacityConfig.from_env()
    assert cfg.window == 2


def test_record_returns_none_when_disabled(tmp_path):
    cfg = CapacityConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CapacityManager(cfg, "myjob")
    result = mgr.record(5.0)
    assert result is None


def test_record_returns_result(tmp_config):
    mgr = CapacityManager(tmp_config, "myjob")
    result = mgr.record(2.0)
    assert isinstance(result, CapacityResult)
    assert result.job == "myjob"
    assert result.duration == pytest.approx(2.0)
    assert result.historical_max == pytest.approx(2.0)
    assert result.utilization == pytest.approx(1.0)
    assert result.near_capacity is True


def test_record_accumulates_samples(tmp_config):
    mgr = CapacityManager(tmp_config, "myjob")
    mgr.record(1.0)
    mgr.record(2.0)
    result = mgr.record(1.5)
    assert result.historical_max == pytest.approx(2.0)
    assert result.duration == pytest.approx(1.5)
    assert result.utilization == pytest.approx(0.75)
    assert result.near_capacity is False


def test_record_respects_window(tmp_config):
    mgr = CapacityManager(tmp_config, "myjob")
    for _ in range(10):
        mgr.record(1.0)
    p = mgr._state_path()
    data = json.loads(p.read_text())
    assert len(data["samples"]) == tmp_config.window


def test_near_capacity_flag_set_correctly(tmp_config):
    mgr = CapacityManager(tmp_config, "myjob")
    mgr.record(10.0)  # establishes max
    result = mgr.record(9.0)  # 90% utilization >= 80% threshold
    assert result.near_capacity is True
    result2 = mgr.record(5.0)  # 50% utilization
    assert result2.near_capacity is False


def test_to_dict_contains_expected_keys(tmp_config):
    mgr = CapacityManager(tmp_config, "myjob")
    result = mgr.record(3.0)
    d = result.to_dict()
    assert set(d.keys()) == {"job", "duration", "historical_max", "utilization", "near_capacity"}
