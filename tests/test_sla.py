"""Tests for cronwrap.sla."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.runner import RunResult
from cronwrap.sla import SLAConfig, SLAManager, SLAViolation


def _result(success: bool = True, duration: float = 1.0) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=0 if success else 1,
        stdout="ok",
        stderr="",
        duration=duration,
        success=success,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return SLAConfig(
        enabled=True,
        max_duration_seconds=5.0,
        max_failures_per_day=2,
        state_dir=str(tmp_path),
        job_name="test_job",
    )


def test_sla_config_disabled_by_default():
    cfg = SLAConfig()
    assert cfg.enabled is False


def test_sla_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SLA_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_SLA_MAX_DURATION", "30")
    monkeypatch.setenv("CRONWRAP_SLA_MAX_FAILURES_PER_DAY", "3")
    monkeypatch.setenv("CRONWRAP_JOB_NAME", "my_job")
    cfg = SLAConfig.from_env()
    assert cfg.enabled is True
    assert cfg.max_duration_seconds == 30.0
    assert cfg.max_failures_per_day == 3
    assert cfg.job_name == "my_job"


def test_check_returns_none_when_disabled():
    cfg = SLAConfig(enabled=False)
    mgr = SLAManager(cfg)
    assert mgr.check(_result(success=False)) is None


def test_check_no_violation_on_success(tmp_config):
    mgr = SLAManager(tmp_config)
    assert mgr.check(_result(success=True, duration=1.0)) is None


def test_check_duration_violation(tmp_config):
    mgr = SLAManager(tmp_config)
    violation = mgr.check(_result(success=True, duration=10.0))
    assert violation is not None
    assert "duration" in violation.reason
    assert violation.value == 10.0
    assert violation.threshold == 5.0


def test_check_failure_count_violation(tmp_config):
    mgr = SLAManager(tmp_config)
    # Record 3 failures (exceeds max of 2)
    for _ in range(3):
        mgr.check(_result(success=False, duration=1.0))
    # 4th failure should trigger violation
    violation = mgr.check(_result(success=False, duration=1.0))
    assert violation is not None
    assert "failures_per_day" in violation.reason


def test_violation_to_dict():
    v = SLAViolation(
        job_name="job",
        reason="max_duration_seconds exceeded",
        value=12.0,
        threshold=5.0,
        timestamp=1000.0,
    )
    d = v.to_dict()
    assert d["job_name"] == "job"
    assert d["reason"] == "max_duration_seconds exceeded"
    assert d["value"] == 12.0
    assert d["threshold"] == 5.0
    assert d["timestamp"] == 1000.0
