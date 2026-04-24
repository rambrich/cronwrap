"""Tests for cronwrap.outlier."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.outlier import OutlierConfig, OutlierDetector, OutlierResult
from cronwrap.runner import RunResult


def _result(duration: float = 1.0, exit_code: int = 0) -> RunResult:
    return RunResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration=duration,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return OutlierConfig(enabled=True, window=10, threshold=2.5, state_dir=str(tmp_path))


def test_outlier_config_disabled_by_default():
    cfg = OutlierConfig()
    assert cfg.enabled is False


def test_outlier_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_OUTLIER_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_OUTLIER_WINDOW", "15")
    monkeypatch.setenv("CRONWRAP_OUTLIER_THRESHOLD", "3.0")
    cfg = OutlierConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 15
    assert cfg.threshold == 3.0


def test_check_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    det = OutlierDetector(tmp_config, job="myjob")
    result = det.check(_result(duration=999.0))
    assert result is None


def test_check_returns_none_with_insufficient_samples(tmp_config):
    det = OutlierDetector(tmp_config, job="myjob")
    # Only 1 sample — not enough to compute stddev
    r = det.check(_result(duration=1.0))
    assert r is None


def test_check_returns_none_with_two_samples(tmp_config):
    det = OutlierDetector(tmp_config, job="myjob")
    det.check(_result(duration=1.0))
    r = det.check(_result(duration=1.1))
    assert r is None


def test_check_detects_normal_run(tmp_config):
    det = OutlierDetector(tmp_config, job="normal")
    durations = [1.0, 1.1, 0.9, 1.0, 1.05]
    for d in durations:
        det.check(_result(duration=d))
    result = det.check(_result(duration=1.02))
    assert isinstance(result, OutlierResult)
    assert result.is_outlier is False


def test_check_detects_outlier_run(tmp_config):
    det = OutlierDetector(tmp_config, job="spike")
    # Establish a tight baseline
    for _ in range(8):
        det.check(_result(duration=1.0))
    # A wildly different value should be flagged
    result = det.check(_result(duration=100.0))
    assert isinstance(result, OutlierResult)
    assert result.is_outlier is True
    assert result.z_score >= tmp_config.threshold


def test_history_persisted(tmp_config):
    det = OutlierDetector(tmp_config, job="persist")
    for d in [1.0, 1.1, 0.9]:
        det.check(_result(duration=d))
    state_file = Path(tmp_config.state_dir) / "persist.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert len(data) == 3


def test_to_dict_contains_keys(tmp_config):
    det = OutlierDetector(tmp_config, job="dict")
    for d in [1.0, 1.0, 1.0, 1.0]:
        det.check(_result(duration=d))
    result = det.check(_result(duration=1.0))
    if result is not None:
        d = result.to_dict()
        assert "is_outlier" in d
        assert "z_score" in d
        assert "mean" in d
