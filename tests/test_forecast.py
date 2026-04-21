"""Tests for cronwrap.forecast."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from cronwrap.forecast import ForecastConfig, ForecastManager, ForecastResult
from cronwrap.runner import RunResult


def _result(success: bool, duration: float = 1.0) -> RunResult:
    r = MagicMock(spec=RunResult)
    r.success = success
    r.duration = duration
    return r


@pytest.fixture()
def tmp_config(tmp_path):
    return ForecastConfig(enabled=True, state_dir=str(tmp_path), window=5)


def test_forecast_config_disabled_by_default():
    cfg = ForecastConfig()
    assert cfg.enabled is False


def test_forecast_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FORECAST_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_FORECAST_WINDOW", "7")
    cfg = ForecastConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 7


def test_forecast_config_invalid_window_defaults(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FORECAST_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_FORECAST_WINDOW", "bad")
    cfg = ForecastConfig.from_env()
    assert cfg.window == 10


def test_predict_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = ForecastManager(config=tmp_config)
    assert mgr.predict("myjob") is None


def test_predict_returns_none_when_no_history(tmp_config):
    mgr = ForecastManager(config=tmp_config)
    assert mgr.predict("myjob") is None


def test_record_and_predict_success(tmp_config):
    mgr = ForecastManager(config=tmp_config)
    for _ in range(4):
        mgr.record("job1", _result(True, 2.0))
    mgr.record("job1", _result(False, 3.0))

    result = mgr.predict("job1")
    assert isinstance(result, ForecastResult)
    assert result.sample_size == 5
    assert result.failure_rate == pytest.approx(0.2)
    assert result.avg_duration == pytest.approx(2.2)
    assert result.predicted_success is True


def test_predict_failure_when_majority_fail(tmp_config):
    mgr = ForecastManager(config=tmp_config)
    for _ in range(3):
        mgr.record("job2", _result(False, 1.0))
    mgr.record("job2", _result(True, 1.0))

    result = mgr.predict("job2")
    assert result is not None
    assert result.predicted_success is False


def test_window_trims_old_entries(tmp_config):
    tmp_config.window = 3
    mgr = ForecastManager(config=tmp_config)
    for _ in range(5):
        mgr.record("job3", _result(True, 1.0))

    path = mgr._state_path("job3")
    entries = json.loads(path.read_text())
    assert len(entries) == 3


def test_record_noop_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = ForecastManager(config=tmp_config)
    mgr.record("job4", _result(True))
    assert not mgr._state_path("job4").exists()


def test_to_dict_keys(tmp_config):
    mgr = ForecastManager(config=tmp_config)
    mgr.record("job5", _result(True, 5.0))
    result = mgr.predict("job5")
    d = result.to_dict()
    assert set(d.keys()) == {"job_id", "sample_size", "failure_rate", "avg_duration", "predicted_success"}
