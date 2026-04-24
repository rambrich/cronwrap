"""Tests for cronwrap.cadence."""
from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest

from cronwrap.cadence import CadenceConfig, CadenceManager, CadenceResult
from cronwrap.runner import RunResult


def _result(success: bool = True) -> RunResult:
    return RunResult(command="echo hi", returncode=0 if success else 1,
                     stdout="", stderr="", duration=1.0, success=success)


@pytest.fixture
def tmp_config(tmp_path):
    return CadenceConfig(
        enabled=True,
        expected_interval_seconds=3600.0,
        tolerance_pct=20.0,
        state_dir=str(tmp_path),
        job_id="test-job",
    )


def test_cadence_config_disabled_by_default():
    cfg = CadenceConfig()
    assert cfg.enabled is False


def test_cadence_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_CADENCE_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_CADENCE_INTERVAL_SECONDS", "1800")
    monkeypatch.setenv("CRONWRAP_CADENCE_TOLERANCE_PCT", "10")
    monkeypatch.setenv("CRONWRAP_JOB_ID", "myjob")
    cfg = CadenceConfig.from_env()
    assert cfg.enabled is True
    assert cfg.expected_interval_seconds == 1800.0
    assert cfg.tolerance_pct == 10.0
    assert cfg.job_id == "myjob"


def test_check_returns_none_when_disabled(tmp_path):
    cfg = CadenceConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CadenceManager(cfg)
    result = mgr.check(_result())
    assert result is None


def test_check_skipped_on_first_run(tmp_config):
    mgr = CadenceManager(tmp_config)
    r = mgr.check(_result())
    assert r is not None
    assert r.skipped is True
    assert r.actual_interval_seconds is None


def test_check_detects_on_time(tmp_config):
    mgr = CadenceManager(tmp_config)
    now = time.time()
    state_path = mgr._state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"last_run_ts": now - 3600}))

    r = mgr.check(_result())
    assert r is not None
    assert not r.is_anomalous()


def test_check_detects_late_run(tmp_config):
    mgr = CadenceManager(tmp_config)
    state_path = mgr._state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    # last run was 5000 seconds ago (expected 3600, tolerance 20% = 720s)
    state_path.write_text(json.dumps({"last_run_ts": time.time() - 5000}))

    r = mgr.check(_result())
    assert r is not None
    assert r.is_late is True
    assert r.is_early is False


def test_check_detects_early_run(tmp_config):
    mgr = CadenceManager(tmp_config)
    state_path = mgr._state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    # last run was only 100 seconds ago
    state_path.write_text(json.dumps({"last_run_ts": time.time() - 100}))

    r = mgr.check(_result())
    assert r is not None
    assert r.is_early is True
    assert r.is_late is False


def test_reset_removes_state(tmp_config):
    mgr = CadenceManager(tmp_config)
    mgr.check(_result())  # creates state
    assert mgr._state_path().exists()
    mgr.reset()
    assert not mgr._state_path().exists()
