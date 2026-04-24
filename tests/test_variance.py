"""Tests for cronwrap.variance."""
import json
import pytest
from unittest.mock import MagicMock

from cronwrap.variance import VarianceConfig, VarianceManager, VarianceResult


def _result(duration: float = 10.0, exit_code: int = 0):
    r = MagicMock()
    r.duration = duration
    r.exit_code = exit_code
    return r


@pytest.fixture
def tmp_config(tmp_path):
    return VarianceConfig(
        enabled=True,
        threshold=2.0,
        min_samples=3,
        state_dir=str(tmp_path / "variance"),
    )


def test_variance_config_disabled_by_default():
    cfg = VarianceConfig()
    assert cfg.enabled is False


def test_variance_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_VARIANCE_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_VARIANCE_THRESHOLD", "3.0")
    monkeypatch.setenv("CRONWRAP_VARIANCE_MIN_SAMPLES", "10")
    cfg = VarianceConfig.from_env()
    assert cfg.enabled is True
    assert cfg.threshold == 3.0
    assert cfg.min_samples == 10


def test_check_returns_none_when_disabled(tmp_path):
    cfg = VarianceConfig(enabled=False, state_dir=str(tmp_path))
    mgr = VarianceManager(cfg)
    assert mgr.check(_result()) is None


def test_check_returns_none_below_min_samples(tmp_config):
    mgr = VarianceManager(tmp_config)
    # min_samples=3, only 2 calls
    mgr.check(_result(10.0))
    result = mgr.check(_result(12.0))
    assert result is None


def test_check_returns_result_at_min_samples(tmp_config):
    mgr = VarianceManager(tmp_config)
    mgr.check(_result(10.0))
    mgr.check(_result(10.0))
    result = mgr.check(_result(10.0))
    assert isinstance(result, VarianceResult)
    assert result.sample_count == 3


def test_check_no_deviation_for_consistent_durations(tmp_config):
    mgr = VarianceManager(tmp_config)
    for _ in range(5):
        mgr.check(_result(10.0))
    result = mgr.check(_result(10.0))
    assert result is not None
    assert result.deviated is False
    assert result.z_score == 0.0


def test_check_detects_deviation(tmp_config):
    mgr = VarianceManager(tmp_config)
    # build stable baseline
    for _ in range(10):
        mgr.check(_result(10.0))
    # inject a very long outlier
    result = mgr.check(_result(1000.0))
    assert result is not None
    assert result.deviated is True
    assert result.z_score > tmp_config.threshold


def test_check_persists_samples(tmp_config, tmp_path):
    mgr = VarianceManager(tmp_config, job_name="myjob")
    mgr.check(_result(5.0))
    mgr.check(_result(6.0))
    state_file = tmp_path / "variance" / "myjob.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert len(data["samples"]) == 2


def test_to_dict_has_expected_keys(tmp_config):
    mgr = VarianceManager(tmp_config)
    mgr.check(_result(10.0))
    mgr.check(_result(10.0))
    result = mgr.check(_result(10.0))
    assert result is not None
    d = result.to_dict()
    assert set(d.keys()) == {"deviated", "duration", "mean", "stddev", "z_score", "sample_count"}
