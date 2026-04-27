"""Tests for cronwrap.burst."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.burst import BurstConfig, BurstManager, BurstResult


@pytest.fixture
def tmp_config(tmp_path):
    return BurstConfig(
        enabled=True,
        window_seconds=60,
        max_runs=3,
        state_dir=str(tmp_path / "burst"),
    )


def test_burst_config_disabled_by_default():
    cfg = BurstConfig()
    assert cfg.enabled is False


def test_burst_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_BURST_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_BURST_WINDOW_SECONDS", "120")
    monkeypatch.setenv("CRONWRAP_BURST_MAX_RUNS", "10")
    cfg = BurstConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 120
    assert cfg.max_runs == 10


def test_record_returns_none_when_disabled(tmp_path):
    cfg = BurstConfig(enabled=False, state_dir=str(tmp_path))
    mgr = BurstManager(config=cfg, job="myjob")
    assert mgr.record() is None


def test_record_returns_result(tmp_config):
    mgr = BurstManager(config=tmp_config, job="myjob")
    result = mgr.record()
    assert isinstance(result, BurstResult)
    assert result.run_count == 1
    assert result.is_burst is False


def test_burst_detected_when_over_limit(tmp_config):
    mgr = BurstManager(config=tmp_config, job="myjob")
    now = time.time()
    for i in range(4):
        result = mgr.record(now=now + i)
    assert result is not None
    assert result.run_count == 4
    assert result.is_burst is True


def test_old_timestamps_pruned(tmp_config):
    mgr = BurstManager(config=tmp_config, job="myjob")
    old = time.time() - 200  # outside 60s window
    mgr._timestamps = [old, old, old, old, old]
    mgr._save_state()
    now = time.time()
    result = mgr.record(now=now)
    assert result is not None
    assert result.run_count == 1
    assert result.is_burst is False


def test_state_persisted(tmp_config):
    mgr1 = BurstManager(config=tmp_config, job="myjob")
    now = time.time()
    mgr1.record(now=now)
    mgr1.record(now=now + 1)

    mgr2 = BurstManager(config=tmp_config, job="myjob")
    result = mgr2.record(now=now + 2)
    assert result is not None
    assert result.run_count == 3


def test_reset_clears_state(tmp_config):
    mgr = BurstManager(config=tmp_config, job="myjob")
    now = time.time()
    mgr.record(now=now)
    mgr.record(now=now + 1)
    mgr.reset()
    result = mgr.record(now=now + 2)
    assert result is not None
    assert result.run_count == 1
