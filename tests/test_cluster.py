"""Tests for cronwrap.cluster."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cronwrap.cluster import ClusterConfig, ClusterManager, ClusterState
from cronwrap.runner import RunResult


def _result(exit_code: int = 0) -> RunResult:
    return RunResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="hi",
        stderr="",
        duration=0.1,
        attempts=1,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return ClusterConfig(enabled=True, state_dir=str(tmp_path), node_id="node-1", stale_seconds=60)


def test_cluster_config_disabled_by_default():
    cfg = ClusterConfig()
    assert cfg.enabled is False


def test_cluster_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_CLUSTER_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_CLUSTER_NODE_ID", "worker-42")
    monkeypatch.setenv("CRONWRAP_CLUSTER_STALE_SECONDS", "120")
    cfg = ClusterConfig.from_env()
    assert cfg.enabled is True
    assert cfg.node_id == "worker-42"
    assert cfg.stale_seconds == 120


def test_record_returns_none_when_disabled(tmp_path):
    cfg = ClusterConfig(enabled=False, state_dir=str(tmp_path))
    mgr = ClusterManager(cfg)
    result = mgr.record("myjob", _result())
    assert result is None


def test_record_writes_state(tmp_config):
    mgr = ClusterManager(tmp_config)
    state = mgr.record("myjob", _result(exit_code=0))
    assert state is not None
    assert state.node_id == "node-1"
    assert state.success is True
    assert state.command == "echo hi"


def test_load_returns_none_when_no_file(tmp_config):
    mgr = ClusterManager(tmp_config)
    assert mgr.load("nonexistent") is None


def test_load_returns_state_after_record(tmp_config):
    mgr = ClusterManager(tmp_config)
    mgr.record("myjob", _result(exit_code=1))
    state = mgr.load("myjob")
    assert state is not None
    assert state.success is False
    assert state.node_id == "node-1"


def test_is_stale_true_when_no_state(tmp_config):
    mgr = ClusterManager(tmp_config)
    assert mgr.is_stale("ghostjob") is True


def test_is_stale_false_for_fresh_record(tmp_config):
    mgr = ClusterManager(tmp_config)
    mgr.record("freshJob", _result())
    assert mgr.is_stale("freshJob") is False


def test_is_stale_true_after_timeout(tmp_config, monkeypatch):
    mgr = ClusterManager(tmp_config)
    mgr.record("oldjob", _result())
    # Advance time past stale threshold
    state = mgr.load("oldjob")
    monkeypatch.setattr(
        "cronwrap.cluster.time.time",
        lambda: state.last_run + tmp_config.stale_seconds + 1,
    )
    assert mgr.is_stale("oldjob") is True
