"""Tests for cronwrap.skew."""
import json
import time
from unittest.mock import patch

import pytest

from cronwrap.skew import SkewConfig, SkewManager, SkewResult


@pytest.fixture
def tmp_config(tmp_path):
    return SkewConfig(
        enabled=True,
        expected_interval_seconds=3600,
        warn_threshold_seconds=60,
        state_dir=str(tmp_path),
    )


def test_skew_config_disabled_by_default():
    cfg = SkewConfig()
    assert cfg.enabled is False


def test_skew_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SKEW_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_SKEW_INTERVAL_SECONDS", "1800")
    monkeypatch.setenv("CRONWRAP_SKEW_WARN_THRESHOLD_SECONDS", "30")
    cfg = SkewConfig.from_env()
    assert cfg.enabled is True
    assert cfg.expected_interval_seconds == 1800
    assert cfg.warn_threshold_seconds == 30


def test_check_returns_none_when_disabled(tmp_path):
    cfg = SkewConfig(enabled=False, state_dir=str(tmp_path))
    mgr = SkewManager(cfg, job="myjob")
    assert mgr.check() is None


def test_check_first_run_not_skewed(tmp_config):
    mgr = SkewManager(tmp_config, job="myjob")
    result = mgr.check()
    assert isinstance(result, SkewResult)
    assert result.skewed is False
    assert result.expected_at is None
    assert "first run" in result.message


def test_check_saves_state(tmp_config, tmp_path):
    mgr = SkewManager(tmp_config, job="myjob")
    mgr.check()
    state_file = tmp_path / "myjob.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert "last_run" in data


def test_check_on_schedule(tmp_config):
    mgr = SkewManager(tmp_config, job="ontime")
    base = time.time()
    with patch("cronwrap.skew.time.time", return_value=base):
        mgr.check()  # first run
    # simulate running exactly on time
    with patch("cronwrap.skew.time.time", return_value=base + 3600):
        result = mgr.check()
    assert result is not None
    assert result.skewed is False
    assert result.delta_seconds < 1.0
    assert "on schedule" in result.message


def test_check_detects_skew(tmp_config):
    mgr = SkewManager(tmp_config, job="late")
    base = time.time()
    with patch("cronwrap.skew.time.time", return_value=base):
        mgr.check()
    # simulate running 10 minutes late
    with patch("cronwrap.skew.time.time", return_value=base + 3600 + 600):
        result = mgr.check()
    assert result is not None
    assert result.skewed is True
    assert result.delta_seconds == pytest.approx(600.0, abs=1.0)
    assert "skew detected" in result.message


def test_to_dict_contains_keys(tmp_config):
    mgr = SkewManager(tmp_config, job="dictjob")
    result = mgr.check()
    d = result.to_dict()
    assert set(d.keys()) == {"skewed", "expected_at", "actual_at", "delta_seconds", "message"}
