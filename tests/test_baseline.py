"""Tests for cronwrap.baseline and cronwrap.baseline_cli."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.baseline import BaselineConfig, BaselineManager, BaselineViolation
from cronwrap.baseline_cli import build_parser, cmd_reset, cmd_status
from cronwrap.runner import RunResult


def _result(command="echo hi", returncode=0, duration=1.0) -> RunResult:
    return RunResult(command=command, returncode=returncode,
                     stdout="", stderr="", duration=duration, timed_out=False)


@pytest.fixture
def tmp_config(tmp_path):
    return BaselineConfig(enabled=True, state_dir=str(tmp_path), min_samples=3, deviation_factor=2.0)


# --- Config tests ---

def test_baseline_config_disabled_by_default():
    cfg = BaselineConfig()
    assert cfg.enabled is False


def test_baseline_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_BASELINE_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_BASELINE_MIN_SAMPLES", "10")
    monkeypatch.setenv("CRONWRAP_BASELINE_DEVIATION_FACTOR", "3.5")
    cfg = BaselineConfig.from_env()
    assert cfg.enabled is True
    assert cfg.min_samples == 10
    assert cfg.deviation_factor == 3.5


# --- Manager tests ---

def test_record_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = BaselineManager(tmp_config)
    result = mgr.record(_result())
    assert result is None


def test_record_accumulates_samples(tmp_config):
    mgr = BaselineManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(duration=1.0))
    stats = mgr.stats("echo hi")
    assert stats["samples"] == 3
    assert abs(stats["avg"] - 1.0) < 0.001


def test_record_no_violation_below_threshold(tmp_config):
    mgr = BaselineManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(duration=1.0))
    # 1.5s < 2.0 * 1.0 avg — no violation
    violation = mgr.record(_result(duration=1.5))
    assert violation is None


def test_record_returns_violation_when_slow(tmp_config):
    mgr = BaselineManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(duration=1.0))
    # 5.0s > 2.0 * 1.0 avg — violation
    violation = mgr.record(_result(duration=5.0))
    assert isinstance(violation, BaselineViolation)
    assert violation.actual_duration == 5.0
    assert violation.avg_duration == pytest.approx(1.0)
    assert violation.factor == pytest.approx(5.0)


def test_violation_str_contains_command(tmp_config):
    v = BaselineViolation(command="my_cmd", avg_duration=1.0, actual_duration=5.0, factor=5.0)
    assert "my_cmd" in str(v)
    assert "5.0x" in str(v)


def test_reset_clears_state(tmp_config):
    mgr = BaselineManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(duration=1.0))
    mgr.reset("echo hi")
    assert mgr.stats("echo hi")["samples"] == 0


def test_stats_returns_none_fields_when_no_data(tmp_config):
    mgr = BaselineManager(tmp_config)
    stats = mgr.stats("nonexistent")
    assert stats["samples"] == 0
    assert stats["avg"] is None


# --- CLI tests ---

def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_status_no_data(tmp_config, capsys):
    mgr = BaselineManager(tmp_config)
    args = MagicMock(cmd="echo hi")
    cmd_status(args, mgr)
    out = capsys.readouterr().out
    assert "No baseline data" in out


def test_cmd_status_shows_stats(tmp_config, capsys):
    mgr = BaselineManager(tmp_config)
    for d in [1.0, 2.0, 3.0]:
        mgr.record(_result(duration=d))
    args = MagicMock(cmd="echo hi")
    cmd_status(args, mgr)
    out = capsys.readouterr().out
    assert "Samples" in out
    assert "Avg" in out


def test_cmd_reset_clears(tmp_config, capsys):
    mgr = BaselineManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(duration=1.0))
    args = MagicMock(cmd="echo hi")
    cmd_reset(args, mgr)
    assert mgr.stats("echo hi")["samples"] == 0
    out = capsys.readouterr().out
    assert "cleared" in out
