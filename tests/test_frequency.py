"""Tests for cronwrap.frequency."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.frequency import FrequencyConfig, FrequencyManager, FrequencyResult
from cronwrap.runner import RunResult


def _result(success: bool = True) -> RunResult:
    r = MagicMock(spec=RunResult)
    r.success = success
    r.returncode = 0 if success else 1
    r.stdout = ""
    r.stderr = ""
    r.duration = 1.0
    return r


@pytest.fixture
def tmp_config(tmp_path):
    return FrequencyConfig(
        enabled=True,
        state_dir=str(tmp_path / "frequency"),
        window_seconds=3600,
        min_runs=1,
        max_runs=5,
    )


def test_frequency_config_disabled_by_default():
    cfg = FrequencyConfig()
    assert cfg.enabled is False


def test_frequency_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FREQUENCY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_FREQUENCY_WINDOW", "1800")
    monkeypatch.setenv("CRONWRAP_FREQUENCY_MIN_RUNS", "2")
    monkeypatch.setenv("CRONWRAP_FREQUENCY_MAX_RUNS", "8")
    cfg = FrequencyConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 1800
    assert cfg.min_runs == 2
    assert cfg.max_runs == 8


def test_record_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = FrequencyManager(tmp_config, "my_job")
    result = mgr.record(_result())
    assert result is None


def test_record_returns_result(tmp_config):
    mgr = FrequencyManager(tmp_config, "my_job")
    result = mgr.record(_result())
    assert isinstance(result, FrequencyResult)
    assert result.job == "my_job"
    assert result.run_count == 1
    assert result.too_infrequent is False
    assert result.too_frequent is False


def test_record_accumulates_runs(tmp_config):
    mgr = FrequencyManager(tmp_config, "accumulate_job")
    for _ in range(3):
        mgr.record(_result())
    result = mgr.record(_result())
    assert result.run_count == 4


def test_record_detects_too_frequent(tmp_config):
    tmp_config.max_runs = 2
    mgr = FrequencyManager(tmp_config, "busy_job")
    for _ in range(3):
        result = mgr.record(_result())
    assert result.too_frequent is True
    assert result.is_anomalous is True


def test_record_prunes_old_timestamps(tmp_config, tmp_path):
    tmp_config.window_seconds = 10
    mgr = FrequencyManager(tmp_config, "prune_job")
    old_ts = time.time() - 9999
    state_file = mgr._state_path()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"timestamps": [old_ts, old_ts]}))
    result = mgr.record(_result())
    assert result.run_count == 1


def test_reset_removes_state(tmp_config):
    mgr = FrequencyManager(tmp_config, "reset_job")
    mgr.record(_result())
    assert mgr._state_path().exists()
    mgr.reset()
    assert not mgr._state_path().exists()


def test_frequency_result_to_dict(tmp_config):
    mgr = FrequencyManager(tmp_config, "dict_job")
    result = mgr.record(_result())
    d = result.to_dict()
    assert d["job"] == "dict_job"
    assert "run_count" in d
    assert "too_frequent" in d
    assert "too_infrequent" in d
