"""Tests for cronwrap.spike."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cronwrap.runner import RunResult
from cronwrap.spike import SpikeConfig, SpikeDetector, SpikeResult


def _result(duration: float = 1.0, returncode: int = 0) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=returncode,
        stdout="hi",
        stderr="",
        duration=duration,
        timed_out=False,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return SpikeConfig(enabled=True, state_dir=str(tmp_path), window=10, z_threshold=3.0, min_samples=5)


def test_spike_config_disabled_by_default():
    cfg = SpikeConfig()
    assert cfg.enabled is False


def test_spike_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SPIKE_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_SPIKE_WINDOW", "15")
    monkeypatch.setenv("CRONWRAP_SPIKE_Z_THRESHOLD", "2.5")
    monkeypatch.setenv("CRONWRAP_SPIKE_MIN_SAMPLES", "3")
    cfg = SpikeConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 15
    assert cfg.z_threshold == 2.5
    assert cfg.min_samples == 3


def test_check_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    det = SpikeDetector(tmp_config, job="myjob")
    assert det.check(_result()) is None


def test_check_insufficient_samples(tmp_config):
    det = SpikeDetector(tmp_config, job="myjob")
    result = det.check(_result(duration=1.0))
    assert result is not None
    assert result.is_spike is False
    assert result.z_score is None
    assert "insufficient" in result.message


def test_check_no_spike_for_normal_duration(tmp_config):
    det = SpikeDetector(tmp_config, job="myjob")
    # Feed stable history
    for _ in range(9):
        det.check(_result(duration=1.0))
    result = det.check(_result(duration=1.1))
    assert result is not None
    assert result.is_spike is False


def test_check_detects_spike(tmp_config):
    det = SpikeDetector(tmp_config, job="spikejob")
    for _ in range(9):
        det.check(_result(duration=1.0))
    # A huge outlier should trigger a spike
    result = det.check(_result(duration=100.0))
    assert result is not None
    assert result.is_spike is True
    assert result.z_score is not None
    assert result.z_score > 3.0
    assert "spike detected" in result.message


def test_check_stores_history(tmp_config, tmp_path):
    det = SpikeDetector(tmp_config, job="historyjob")
    for i in range(6):
        det.check(_result(duration=float(i + 1)))
    state_file = tmp_path / "historyjob.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert len(data) == 6


def test_reset_removes_state(tmp_config, tmp_path):
    det = SpikeDetector(tmp_config, job="resetjob")
    for _ in range(6):
        det.check(_result(duration=1.0))
    det.reset()
    assert not (tmp_path / "resetjob.json").exists()


def test_to_dict_has_expected_keys(tmp_config):
    det = SpikeDetector(tmp_config, job="dictjob")
    for _ in range(9):
        det.check(_result(duration=1.0))
    result = det.check(_result(duration=1.0))
    d = result.to_dict()
    assert "is_spike" in d
    assert "z_score" in d
    assert "duration" in d
    assert "mean_duration" in d
    assert "message" in d
