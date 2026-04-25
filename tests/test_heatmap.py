"""Tests for cronwrap.heatmap."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from cronwrap.heatmap import HeatmapConfig, HeatmapManager, HeatmapState
from cronwrap.runner import RunResult


def _result(success: bool = True) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=0 if success else 1,
        stdout="hi",
        stderr="",
        duration=1.0,
        success=success,
    )


@pytest.fixture()
def tmp_config(tmp_path):
    return HeatmapConfig(enabled=True, state_dir=str(tmp_path))


def test_heatmap_config_disabled_by_default():
    cfg = HeatmapConfig()
    assert cfg.enabled is False


def test_heatmap_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_HEATMAP_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_HEATMAP_STATE_DIR", "/tmp/hm")
    cfg = HeatmapConfig.from_env()
    assert cfg.enabled is True
    assert cfg.state_dir == "/tmp/hm"


def test_record_returns_none_when_disabled(tmp_path):
    cfg = HeatmapConfig(enabled=False, state_dir=str(tmp_path))
    mgr = HeatmapManager(cfg, "myjob")
    assert mgr.record(_result()) is None


def test_record_writes_entry(tmp_config):
    mgr = HeatmapManager(tmp_config, "myjob")
    ts = datetime(2024, 6, 3, 14, 0, 0)  # Monday (weekday=0), hour=14
    state = mgr.record(_result(), ts=ts)
    assert state is not None
    assert state.counts["0"]["14"] == 1


def test_record_accumulates(tmp_config):
    mgr = HeatmapManager(tmp_config, "myjob")
    ts = datetime(2024, 6, 3, 14, 0, 0)
    mgr.record(_result(), ts=ts)
    mgr.record(_result(), ts=ts)
    state = mgr.load()
    assert state is not None
    assert state.counts["0"]["14"] == 2


def test_hottest_slot(tmp_config):
    mgr = HeatmapManager(tmp_config, "myjob")
    mgr.record(_result(), ts=datetime(2024, 6, 3, 9, 0))   # Mon 09
    mgr.record(_result(), ts=datetime(2024, 6, 3, 9, 0))   # Mon 09
    mgr.record(_result(), ts=datetime(2024, 6, 4, 10, 0))  # Tue 10
    state = mgr.load()
    assert state is not None
    assert state.hottest_slot() == (0, 9)


def test_load_returns_none_when_disabled(tmp_path):
    cfg = HeatmapConfig(enabled=False, state_dir=str(tmp_path))
    mgr = HeatmapManager(cfg, "myjob")
    assert mgr.load() is None


def test_load_returns_empty_state_when_no_file(tmp_config):
    mgr = HeatmapManager(tmp_config, "newjob")
    state = mgr.load()
    assert state is not None
    assert state.counts == {}


def test_state_persisted_as_json(tmp_config):
    mgr = HeatmapManager(tmp_config, "myjob")
    mgr.record(_result(), ts=datetime(2024, 6, 5, 8, 0))  # Wed 08
    p = mgr._state_path()
    data = json.loads(p.read_text())
    assert data["job"] == "myjob"
    assert data["counts"]["2"]["8"] == 1
