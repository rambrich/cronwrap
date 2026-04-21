"""Tests for cronwrap.drift."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.drift import DriftConfig, DriftManager, DriftResult


@pytest.fixture()
def tmp_config(tmp_path):
    return DriftConfig(enabled=True, state_dir=str(tmp_path), warn_seconds=30.0, crit_seconds=120.0)


def test_drift_config_disabled_by_default():
    cfg = DriftConfig()
    assert cfg.enabled is False


def test_drift_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DRIFT_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_DRIFT_WARN_SECONDS", "45")
    monkeypatch.setenv("CRONWRAP_DRIFT_CRIT_SECONDS", "200")
    cfg = DriftConfig.from_env()
    assert cfg.enabled is True
    assert cfg.warn_seconds == 45.0
    assert cfg.crit_seconds == 200.0


def test_drift_config_invalid_seconds_defaults(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DRIFT_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_DRIFT_WARN_SECONDS", "bad")
    monkeypatch.setenv("CRONWRAP_DRIFT_CRIT_SECONDS", "also_bad")
    cfg = DriftConfig.from_env()
    assert cfg.warn_seconds == 60.0
    assert cfg.crit_seconds == 300.0


def test_check_returns_none_when_disabled(tmp_path):
    cfg = DriftConfig(enabled=False, state_dir=str(tmp_path))
    mgr = DriftManager(cfg)
    result = mgr.check("myjob")
    assert result is None


def test_check_returns_none_when_no_state(tmp_config):
    mgr = DriftManager(tmp_config)
    result = mgr.check("myjob")
    assert result is None


def test_record_expected_creates_file(tmp_config, tmp_path):
    mgr = DriftManager(tmp_config)
    mgr.record_expected("myjob", expected_at=1000.0)
    state_file = Path(tmp_config.state_dir) / "myjob.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["expected_at"] == 1000.0


def test_record_noop_when_disabled(tmp_path):
    cfg = DriftConfig(enabled=False, state_dir=str(tmp_path))
    mgr = DriftManager(cfg)
    mgr.record_expected("myjob", expected_at=1000.0)
    state_file = Path(str(tmp_path)) / "myjob.json"
    assert not state_file.exists()


def test_check_no_drift(tmp_config):
    mgr = DriftManager(tmp_config)
    now = time.time()
    mgr.record_expected("myjob", expected_at=now)
    result = mgr.check("myjob", actual_at=now + 5)
    assert isinstance(result, DriftResult)
    assert result.drift_seconds == pytest.approx(5.0)
    assert result.is_warning is False
    assert result.is_critical is False


def test_check_warning_drift(tmp_config):
    mgr = DriftManager(tmp_config)
    now = time.time()
    mgr.record_expected("myjob", expected_at=now)
    result = mgr.check("myjob", actual_at=now + 60)
    assert result.is_warning is True
    assert result.is_critical is False


def test_check_critical_drift(tmp_config):
    mgr = DriftManager(tmp_config)
    now = time.time()
    mgr.record_expected("myjob", expected_at=now)
    result = mgr.check("myjob", actual_at=now + 200)
    assert result.is_warning is True
    assert result.is_critical is True


def test_reset_removes_state(tmp_config):
    mgr = DriftManager(tmp_config)
    mgr.record_expected("myjob", expected_at=1000.0)
    mgr.reset("myjob")
    assert mgr.check("myjob") is None


def test_to_dict_has_expected_keys(tmp_config):
    mgr = DriftManager(tmp_config)
    now = time.time()
    mgr.record_expected("myjob", expected_at=now)
    result = mgr.check("myjob", actual_at=now + 10)
    d = result.to_dict()
    assert set(d.keys()) == {"job", "expected_at", "actual_at", "drift_seconds", "is_warning", "is_critical"}
