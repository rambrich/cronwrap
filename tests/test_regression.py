"""Tests for cronwrap.regression."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from cronwrap.regression import RegressionConfig, RegressionDetector, RegressionResult
from cronwrap.runner import RunResult


def _result(returncode: int = 0) -> RunResult:
    r = MagicMock(spec=RunResult)
    r.returncode = returncode
    return r


@pytest.fixture()
def tmp_config(tmp_path):
    return RegressionConfig(
        enabled=True,
        window=5,
        threshold=0.6,
        state_dir=str(tmp_path),
    )


# --- config ---

def test_regression_config_disabled_by_default():
    cfg = RegressionConfig()
    assert cfg.enabled is False


def test_regression_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_REGRESSION_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_REGRESSION_WINDOW", "20")
    monkeypatch.setenv("CRONWRAP_REGRESSION_THRESHOLD", "0.8")
    cfg = RegressionConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 20
    assert cfg.threshold == 0.8


def test_regression_config_clamps_threshold(monkeypatch):
    monkeypatch.setenv("CRONWRAP_REGRESSION_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_REGRESSION_THRESHOLD", "1.5")
    cfg = RegressionConfig.from_env()
    assert cfg.threshold == 1.0


def test_regression_config_invalid_threshold_defaults(monkeypatch):
    monkeypatch.setenv("CRONWRAP_REGRESSION_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_REGRESSION_THRESHOLD", "bad")
    cfg = RegressionConfig.from_env()
    assert cfg.threshold == 0.5


# --- detector ---

def test_record_returns_none_when_disabled(tmp_path):
    cfg = RegressionConfig(enabled=False, state_dir=str(tmp_path))
    det = RegressionDetector(cfg)
    result = det.record("myjob", _result(1))
    assert result is None


def test_record_returns_none_before_window_full(tmp_config):
    det = RegressionDetector(tmp_config)
    for _ in range(tmp_config.window - 1):
        r = det.record("myjob", _result(1))
    assert r is None


def test_record_returns_result_when_window_full(tmp_config):
    det = RegressionDetector(tmp_config)
    for _ in range(tmp_config.window):
        r = det.record("myjob", _result(0))
    assert isinstance(r, RegressionResult)
    assert r.job == "myjob"
    assert r.window == tmp_config.window


def test_record_detects_regression(tmp_config):
    det = RegressionDetector(tmp_config)
    # all failures → success_rate = 0.0 < threshold 0.6
    for _ in range(tmp_config.window):
        r = det.record("myjob", _result(1))
    assert r is not None
    assert r.is_regression is True
    assert r.success_rate == 0.0


def test_record_no_regression_on_high_success(tmp_config):
    det = RegressionDetector(tmp_config)
    for _ in range(tmp_config.window):
        r = det.record("myjob", _result(0))
    assert r is not None
    assert r.is_regression is False
    assert r.success_rate == 1.0


def test_record_persists_history(tmp_config, tmp_path):
    det = RegressionDetector(tmp_config)
    det.record("myjob", _result(0))
    state_files = list(tmp_path.iterdir())
    assert len(state_files) == 1
    data = json.loads(state_files[0].read_text())
    assert data == [True]


def test_to_dict_contains_expected_keys(tmp_config):
    det = RegressionDetector(tmp_config)
    for _ in range(tmp_config.window):
        r = det.record("myjob", _result(0))
    d = r.to_dict()
    assert set(d.keys()) == {"job", "success_rate", "window", "is_regression"}
