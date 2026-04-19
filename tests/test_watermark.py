"""Tests for cronwrap.watermark."""
import json
import pytest
from unittest.mock import MagicMock
from cronwrap.watermark import WatermarkConfig, WatermarkManager, WatermarkState
from cronwrap.runner import RunResult


def _result(command="echo hi", exit_code=0, duration=1.5):
    r = MagicMock(spec=RunResult)
    r.command = command
    r.exit_code = exit_code
    r.duration = duration
    return r


@pytest.fixture
def tmp_config(tmp_path):
    return WatermarkConfig(enabled=True, state_dir=str(tmp_path))


def test_watermark_config_disabled_by_default():
    cfg = WatermarkConfig()
    assert cfg.enabled is False


def test_watermark_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_WATERMARK_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_WATERMARK_DIR", "/tmp/wm")
    cfg = WatermarkConfig.from_env()
    assert cfg.enabled is True
    assert cfg.state_dir == "/tmp/wm"


def test_record_returns_none_when_disabled():
    mgr = WatermarkManager(WatermarkConfig(enabled=False))
    assert mgr.record(_result()) is None


def test_load_returns_none_when_disabled():
    mgr = WatermarkManager(WatermarkConfig(enabled=False))
    assert mgr.load("echo hi") is None


def test_load_returns_none_when_no_file(tmp_config):
    mgr = WatermarkManager(tmp_config)
    assert mgr.load("echo hi") is None


def test_record_creates_state(tmp_config):
    mgr = WatermarkManager(tmp_config)
    state = mgr.record(_result(duration=2.0))
    assert state is not None
    assert state.max_duration == 2.0
    assert state.min_duration == 2.0
    assert state.total_runs == 1


def test_record_updates_max_duration(tmp_config):
    mgr = WatermarkManager(tmp_config)
    mgr.record(_result(duration=1.0))
    state = mgr.record(_result(duration=3.0))
    assert state.max_duration == 3.0
    assert state.min_duration == 1.0
    assert state.total_runs == 2


def test_record_tracks_max_exit_code(tmp_config):
    mgr = WatermarkManager(tmp_config)
    mgr.record(_result(exit_code=0))
    state = mgr.record(_result(exit_code=1))
    assert state.max_exit_code == 1


def test_state_to_dict_and_from_dict():
    s = WatermarkState(command="ls", max_duration=5.0, min_duration=1.0, max_exit_code=2, total_runs=3)
    d = s.to_dict()
    s2 = WatermarkState.from_dict(d)
    assert s2.command == "ls"
    assert s2.max_duration == 5.0
    assert s2.total_runs == 3
