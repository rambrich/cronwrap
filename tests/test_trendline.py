"""Tests for cronwrap.trendline."""
from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from cronwrap.trendline import TrendlineConfig, TrendlineManager, TrendResult


def _result(duration: float = 1.0, exit_code: int = 0):
    r = MagicMock()
    r.duration = duration
    r.exit_code = exit_code
    return r


@pytest.fixture
def tmp_config(tmp_path):
    return TrendlineConfig(enabled=True, state_dir=str(tmp_path), window=3, threshold=0.20)


def test_trendline_config_disabled_by_default():
    cfg = TrendlineConfig()
    assert cfg.enabled is False


def test_trendline_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_TRENDLINE_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_TRENDLINE_WINDOW", "5")
    monkeypatch.setenv("CRONWRAP_TRENDLINE_THRESHOLD", "0.15")
    cfg = TrendlineConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 5
    assert cfg.threshold == pytest.approx(0.15)


def test_record_returns_none_when_disabled(tmp_path):
    cfg = TrendlineConfig(enabled=False, state_dir=str(tmp_path))
    mgr = TrendlineManager(cfg)
    assert mgr.record(_result(2.0)) is None


def test_record_returns_insufficient_data_initially(tmp_config):
    mgr = TrendlineManager(tmp_config)
    result = mgr.record(_result(1.0))
    assert result is not None
    assert result.direction == "insufficient_data"


def test_record_detects_degrading_trend(tmp_config):
    mgr = TrendlineManager(tmp_config)
    # window=3: need 6 samples to compare two full windows
    for _ in range(3):
        mgr.record(_result(1.0))
    for _ in range(3):
        mgr.record(_result(2.0))  # 100% increase — degrading
    result = mgr.record(_result(2.0))
    assert result.direction == "degrading"
    assert result.is_degrading() is True


def test_record_detects_improving_trend(tmp_config):
    mgr = TrendlineManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(2.0))
    for _ in range(3):
        mgr.record(_result(1.0))  # 50% decrease — improving
    result = mgr.record(_result(1.0))
    assert result.direction == "improving"
    assert result.is_improving() is True


def test_record_detects_stable_trend(tmp_config):
    mgr = TrendlineManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(1.0))
    for _ in range(4):
        mgr.record(_result(1.05))  # 5% — within 20% threshold
    result = mgr.analyze(mgr._load_durations())
    assert result.direction == "stable"


def test_state_persisted_across_instances(tmp_config):
    mgr1 = TrendlineManager(tmp_config, job_name="myjob")
    mgr1.record(_result(1.0))
    mgr2 = TrendlineManager(tmp_config, job_name="myjob")
    durations = mgr2._load_durations()
    assert len(durations) == 1
    assert durations[0] == pytest.approx(1.0)
