"""Tests for cronwrap.budget."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.budget import BudgetConfig, BudgetExceededError, BudgetManager
from cronwrap.runner import RunResult


def _result(duration: float = 10.0, exit_code: int = 0) -> RunResult:
    return RunResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration=duration,
        timed_out=False,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return BudgetConfig(enabled=True, max_seconds_per_day=100.0, state_dir=str(tmp_path))


def test_budget_config_disabled_by_default():
    cfg = BudgetConfig()
    assert cfg.enabled is False


def test_budget_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_BUDGET_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_BUDGET_MAX_SECONDS_PER_DAY", "7200")
    cfg = BudgetConfig.from_env()
    assert cfg.enabled is True
    assert cfg.max_seconds_per_day == 7200.0


def test_check_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = BudgetManager(tmp_config)
    assert mgr.check() is None


def test_check_passes_initially(tmp_config):
    mgr = BudgetManager(tmp_config)
    assert mgr.check() is None


def test_record_accumulates(tmp_config):
    mgr = BudgetManager(tmp_config)
    mgr.record(_result(30.0))
    mgr.record(_result(40.0))
    assert mgr.remaining() == pytest.approx(30.0)


def test_check_raises_when_exceeded(tmp_config):
    mgr = BudgetManager(tmp_config)
    mgr.record(_result(110.0))
    err = mgr.check()
    assert isinstance(err, BudgetExceededError)
    assert err.used >= 110.0


def test_record_noop_when_disabled(tmp_config, tmp_path):
    tmp_config.enabled = False
    mgr = BudgetManager(tmp_config)
    mgr.record(_result(999.0))
    state_file = tmp_path / "budget_default.json"
    assert not state_file.exists()


def test_state_resets_on_new_day(tmp_config, tmp_path):
    mgr = BudgetManager(tmp_config)
    state_path = tmp_path / "budget_default.json"
    state_path.write_text(json.dumps({"date": "2000-01-01", "total_seconds": 99.0}))
    assert mgr.remaining() == pytest.approx(100.0)
