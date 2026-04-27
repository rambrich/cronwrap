"""Tests for cronwrap.cardinality."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.cardinality import (
    CardinalityConfig,
    CardinalityManager,
    CardinalityResult,
)
from cronwrap.runner import RunResult


def _result(stdout: str = "ok", stderr: str = "", exit_code: int = 0) -> RunResult:
    return RunResult(command="echo test", exit_code=exit_code,
                     stdout=stdout, stderr=stderr, duration=0.1)


@pytest.fixture
def tmp_config(tmp_path):
    return CardinalityConfig(
        enabled=True,
        window_seconds=3600,
        max_unique=3,
        state_dir=str(tmp_path),
    )


def test_cardinality_config_disabled_by_default():
    cfg = CardinalityConfig()
    assert cfg.enabled is False


def test_cardinality_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_CARDINALITY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_CARDINALITY_WINDOW", "7200")
    monkeypatch.setenv("CRONWRAP_CARDINALITY_MAX_UNIQUE", "10")
    cfg = CardinalityConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 7200
    assert cfg.max_unique == 10


def test_record_returns_none_when_disabled(tmp_path):
    cfg = CardinalityConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CardinalityManager(cfg, job="myjob")
    assert mgr.record(_result()) is None


def test_record_returns_result(tmp_config):
    mgr = CardinalityManager(tmp_config, job="myjob")
    r = mgr.record(_result(stdout="hello"))
    assert isinstance(r, CardinalityResult)
    assert r.unique_count == 1
    assert r.exceeded is False


def test_unique_count_increments_for_new_output(tmp_config):
    mgr = CardinalityManager(tmp_config, job="myjob")
    mgr.record(_result(stdout="output-a"))
    mgr.record(_result(stdout="output-b"))
    r = mgr.record(_result(stdout="output-c"))
    assert r.unique_count == 3
    assert r.exceeded is False


def test_exceeded_when_over_max(tmp_config):
    mgr = CardinalityManager(tmp_config, job="myjob")
    mgr.record(_result(stdout="a"))
    mgr.record(_result(stdout="b"))
    mgr.record(_result(stdout="c"))
    r = mgr.record(_result(stdout="d"))  # 4 unique, max is 3
    assert r.unique_count == 4
    assert r.exceeded is True


def test_duplicate_output_not_counted_twice(tmp_config):
    mgr = CardinalityManager(tmp_config, job="myjob")
    mgr.record(_result(stdout="same"))
    r = mgr.record(_result(stdout="same"))
    assert r.unique_count == 1


def test_reset_clears_state(tmp_config, tmp_path):
    mgr = CardinalityManager(tmp_config, job="myjob")
    mgr.record(_result(stdout="data"))
    state_files = list(Path(str(tmp_path)).glob("*.json"))
    assert len(state_files) == 1
    mgr.reset()
    state_files = list(Path(str(tmp_path)).glob("*.json"))
    assert len(state_files) == 0
