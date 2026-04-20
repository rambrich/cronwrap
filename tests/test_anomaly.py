"""Tests for cronwrap.anomaly."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.anomaly import AnomalyConfig, AnomalyDetector, AnomalyResult
from cronwrap.runner import RunResult


def _result(duration: float = 1.0, returncode: int = 0) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=returncode,
        stdout="hi",
        stderr="",
        duration=duration,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return AnomalyConfig(
        enabled=True,
        state_dir=str(tmp_path / "anomaly"),
        window=10,
        z_score_threshold=2.0,
        min_samples=3,
    )


def test_anomaly_config_disabled_by_default():
    cfg = AnomalyConfig()
    assert cfg.enabled is False


def test_anomaly_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_ANOMALY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_ANOMALY_WINDOW", "15")
    monkeypatch.setenv("CRONWRAP_ANOMALY_Z_SCORE", "3.0")
    monkeypatch.setenv("CRONWRAP_ANOMALY_MIN_SAMPLES", "8")
    cfg = AnomalyConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 15
    assert cfg.z_score_threshold == 3.0
    assert cfg.min_samples == 8


def test_check_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    det = AnomalyDetector(tmp_config, job_id="job1")
    result = det.check(_result(1.0))
    assert result is None


def test_check_insufficient_samples(tmp_config):
    det = AnomalyDetector(tmp_config, job_id="job2")
    # Only one sample — below min_samples=3
    r = det.check(_result(1.0))
    assert r is not None
    assert r.is_anomaly is False
    assert r.reason == "insufficient samples"
    assert r.z_score is None


def test_check_no_anomaly_for_normal_duration(tmp_config):
    det = AnomalyDetector(tmp_config, job_id="job3")
    # Populate history with stable durations
    for _ in range(6):
        det.check(_result(1.0))
    r = det.check(_result(1.05))
    assert r is not None
    assert r.is_anomaly is False


def test_check_detects_anomaly(tmp_config):
    det = AnomalyDetector(tmp_config, job_id="job4")
    for _ in range(6):
        det.check(_result(1.0))
    # Dramatically different duration should trigger anomaly
    r = det.check(_result(50.0))
    assert r is not None
    assert r.is_anomaly is True
    assert r.z_score is not None
    assert r.z_score >= tmp_config.z_score_threshold


def test_history_persisted(tmp_config):
    det = AnomalyDetector(tmp_config, job_id="job5")
    det.check(_result(1.0))
    det.check(_result(2.0))
    history = det._load_history()
    assert len(history) == 2
    assert 1.0 in history
    assert 2.0 in history


def test_window_limits_history_size(tmp_config):
    tmp_config.window = 5
    det = AnomalyDetector(tmp_config, job_id="job6")
    for i in range(20):
        det.check(_result(float(i)))
    history = det._load_history()
    assert len(history) <= 5
