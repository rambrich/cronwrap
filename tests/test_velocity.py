"""Tests for cronwrap.velocity."""
import json
import time
from pathlib import Path

import pytest

from cronwrap.runner import RunResult
from cronwrap.velocity import VelocityConfig, VelocityManager, VelocityResult


def _result(success: bool = True, duration: float = 1.0) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=0 if success else 1,
        stdout="ok",
        stderr="",
        duration=duration,
        timed_out=False,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return VelocityConfig(
        enabled=True,
        window_seconds=3600,
        min_runs=3,
        spike_factor=2.0,
        state_dir=str(tmp_path),
    )


def test_velocity_config_disabled_by_default():
    cfg = VelocityConfig()
    assert cfg.enabled is False


def test_velocity_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_VELOCITY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_VELOCITY_WINDOW", "1800")
    monkeypatch.setenv("CRONWRAP_VELOCITY_MIN_RUNS", "4")
    monkeypatch.setenv("CRONWRAP_VELOCITY_SPIKE_FACTOR", "3.0")
    cfg = VelocityConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 1800
    assert cfg.min_runs == 4
    assert cfg.spike_factor == 3.0


def test_record_returns_none_when_disabled(tmp_path):
    cfg = VelocityConfig(enabled=False, state_dir=str(tmp_path))
    mgr = VelocityManager(config=cfg, job="myjob")
    assert mgr.record(_result()) is None


def test_record_writes_timestamps(tmp_config, tmp_path):
    mgr = VelocityManager(config=tmp_config, job="myjob")
    mgr.record(_result())
    state_file = tmp_path / "myjob.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert len(data) == 1


def test_record_returns_velocity_result(tmp_config):
    mgr = VelocityManager(config=tmp_config, job="myjob")
    result = mgr.record(_result())
    assert isinstance(result, VelocityResult)
    assert result.job == "myjob"
    assert result.run_count == 1
    assert result.is_spike is False


def test_record_accumulates_runs(tmp_config):
    mgr = VelocityManager(config=tmp_config, job="myjob")
    for _ in range(4):
        result = mgr.record(_result())
    assert result.run_count == 4


def test_reset_removes_state(tmp_config, tmp_path):
    mgr = VelocityManager(config=tmp_config, job="myjob")
    mgr.record(_result())
    assert (tmp_path / "myjob.json").exists()
    mgr.reset()
    assert not (tmp_path / "myjob.json").exists()


def test_to_dict_keys(tmp_config):
    mgr = VelocityManager(config=tmp_config, job="myjob")
    result = mgr.record(_result())
    d = result.to_dict()
    assert "job" in d
    assert "run_count" in d
    assert "rate_per_hour" in d
    assert "is_spike" in d
