"""Tests for cronwrap.cluster_cli."""
from __future__ import annotations

import argparse
import time
from unittest.mock import MagicMock

import pytest

from cronwrap.cluster import ClusterConfig, ClusterManager, ClusterState
from cronwrap.cluster_cli import build_parser, cmd_reset, cmd_status


def _state(node_id: str = "node-1", success: bool = True) -> ClusterState:
    return ClusterState(
        node_id=node_id,
        last_run=time.time() - 30,
        success=success,
        command="backup.sh",
    )


@pytest.fixture
def tmp_mgr(tmp_path):
    cfg = ClusterConfig(enabled=True, state_dir=str(tmp_path), node_id="node-1", stale_seconds=60)
    return ClusterManager(cfg)


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_status_no_state(tmp_mgr, capsys):
    args = argparse.Namespace(job="unknown")
    cmd_status(args, mgr=tmp_mgr)
    out = capsys.readouterr().out
    assert "No cluster state" in out


def test_cmd_status_shows_state(tmp_mgr, capsys):
    from cronwrap.runner import RunResult
    result = RunResult(command="backup.sh", exit_code=0, stdout="", stderr="", duration=1.0, attempts=1)
    tmp_mgr.record("myjob", result)
    args = argparse.Namespace(job="myjob")
    cmd_status(args, mgr=tmp_mgr)
    out = capsys.readouterr().out
    assert "node-1" in out
    assert "Stale" in out


def test_cmd_reset_removes_file(tmp_mgr, capsys):
    from cronwrap.runner import RunResult
    result = RunResult(command="backup.sh", exit_code=0, stdout="", stderr="", duration=1.0, attempts=1)
    tmp_mgr.record("myjob", result)
    path = tmp_mgr._state_path("myjob")
    assert path.exists()
    args = argparse.Namespace(job="myjob")
    cmd_reset(args, mgr=tmp_mgr)
    assert not path.exists()
    out = capsys.readouterr().out
    assert "cleared" in out


def test_cmd_reset_no_state_prints_message(tmp_mgr, capsys):
    args = argparse.Namespace(job="ghost")
    cmd_reset(args, mgr=tmp_mgr)
    out = capsys.readouterr().out
    assert "No state" in out
