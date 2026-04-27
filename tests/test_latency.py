"""Tests for cronwrap.latency."""
import json
import pytest
from unittest.mock import MagicMock

from cronwrap.latency import LatencyConfig, LatencyManager, LatencyResult
from cronwrap.runner import RunResult


def _result(duration: float = 5.0, exit_code: int = 0) -> RunResult:
    r = MagicMock(spec=RunResult)
    r.duration = duration
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    return r


@pytest.fixture
def tmp_config(tmp_path):
    return LatencyConfig(
        enabled=True,
        warn_seconds=10.0,
        crit_seconds=30.0,
        state_dir=str(tmp_path),
        window=5,
    )


def test_latency_config_disabled_by_default():
    cfg = LatencyConfig()
    assert cfg.enabled is False


def test_latency_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_LATENCY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_LATENCY_WARN_SECONDS", "15")
    monkeypatch.setenv("CRONWRAP_LATENCY_CRIT_SECONDS", "60")
    monkeypatch.setenv("CRONWRAP_LATENCY_WINDOW", "10")
    cfg = LatencyConfig.from_env()
    assert cfg.enabled is True
    assert cfg.warn_seconds == 15.0
    assert cfg.crit_seconds == 60.0
    assert cfg.window == 10


def test_record_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = LatencyManager(tmp_config, "myjob")
    assert mgr.record(_result()) is None


def test_record_returns_result(tmp_config):
    mgr = LatencyManager(tmp_config, "myjob")
    res = mgr.record(_result(duration=5.0))
    assert isinstance(res, LatencyResult)
    assert res.duration == 5.0
    assert res.sample_count == 1
    assert res.is_warn is False
    assert res.is_crit is False


def test_record_detects_warn(tmp_config):
    mgr = LatencyManager(tmp_config, "myjob")
    res = mgr.record(_result(duration=15.0))
    assert res.is_warn is True
    assert res.is_crit is False


def test_record_detects_crit(tmp_config):
    mgr = LatencyManager(tmp_config, "myjob")
    res = mgr.record(_result(duration=45.0))
    assert res.is_warn is True
    assert res.is_crit is True


def test_record_accumulates_samples(tmp_config):
    mgr = LatencyManager(tmp_config, "myjob")
    mgr.record(_result(duration=2.0))
    mgr.record(_result(duration=4.0))
    res = mgr.record(_result(duration=6.0))
    assert res.sample_count == 3
    assert res.avg_duration == pytest.approx(4.0)


def test_record_respects_window(tmp_config):
    tmp_config.window = 3
    mgr = LatencyManager(tmp_config, "myjob")
    for d in [1.0, 2.0, 3.0, 4.0, 5.0]:
        res = mgr.record(_result(duration=d))
    assert res.sample_count == 3


def test_reset_clears_state(tmp_config):
    mgr = LatencyManager(tmp_config, "myjob")
    mgr.record(_result(duration=5.0))
    mgr.reset()
    samples = mgr._load_samples()
    assert samples == []
