"""Tests for cronwrap.percentile."""
import json
import pytest
from unittest.mock import MagicMock

from cronwrap.percentile import PercentileConfig, PercentileManager, PercentileResult


def _result(command="echo hi", returncode=0, duration=1.0):
    r = MagicMock()
    r.command = command
    r.returncode = returncode
    r.duration = duration
    return r


@pytest.fixture
def tmp_config(tmp_path):
    return PercentileConfig(
        enabled=True,
        state_dir=str(tmp_path / "percentile"),
        window=10,
    )


def test_percentile_config_disabled_by_default():
    cfg = PercentileConfig()
    assert cfg.enabled is False


def test_percentile_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_PERCENTILE_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_PERCENTILE_WINDOW", "50")
    cfg = PercentileConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 50


def test_record_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = PercentileManager(tmp_config)
    result = mgr.record(_result())
    assert result is None


def test_record_returns_percentile_result(tmp_config):
    mgr = PercentileManager(tmp_config)
    res = mgr.record(_result(duration=2.0))
    assert isinstance(res, PercentileResult)
    assert res.sample_count == 1
    assert res.p50 == 2.0


def test_percentile_accumulates_samples(tmp_config):
    mgr = PercentileManager(tmp_config)
    durations = [1.0, 2.0, 3.0, 4.0, 5.0]
    for d in durations:
        res = mgr.record(_result(duration=d))
    assert res.sample_count == 5
    assert res.p50 == 3.0
    assert res.p99 == 5.0


def test_window_trims_old_samples(tmp_config):
    tmp_config.window = 3
    mgr = PercentileManager(tmp_config)
    for d in [10.0, 20.0, 30.0, 1.0, 2.0, 3.0]:
        mgr.record(_result(duration=d))
    res = mgr.get("echo hi")
    assert res.sample_count == 3
    # last 3 samples: 1.0, 2.0, 3.0
    assert res.p50 == 2.0


def test_get_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = PercentileManager(tmp_config)
    assert mgr.get("echo hi") is None


def test_get_returns_none_when_no_data(tmp_config):
    mgr = PercentileManager(tmp_config)
    assert mgr.get("nonexistent") is None


def test_reset_removes_state(tmp_config):
    mgr = PercentileManager(tmp_config)
    mgr.record(_result(duration=1.5))
    mgr.reset("echo hi")
    assert mgr.get("echo hi") is None


def test_to_dict_has_expected_keys(tmp_config):
    mgr = PercentileManager(tmp_config)
    mgr.record(_result(duration=1.0))
    res = mgr.get("echo hi")
    d = res.to_dict()
    assert "job" in d
    assert "sample_count" in d
    assert "p50" in d
    assert "p95" in d
    assert "p99" in d


def test_p50_disabled_via_config(tmp_config):
    tmp_config.p50 = False
    mgr = PercentileManager(tmp_config)
    res = mgr.record(_result(duration=2.0))
    assert res.p50 is None
    assert res.p95 is not None
