"""Tests for cronwrap.budget_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.budget_cli import build_parser, cmd_reset, cmd_status
from cronwrap.budget import BudgetConfig, BudgetManager
from cronwrap.runner import RunResult


def _result(duration: float = 20.0) -> RunResult:
    return RunResult(
        command="echo", exit_code=0, stdout="", stderr="", duration=duration, timed_out=False
    )


@pytest.fixture
def tmp_mgr(tmp_path, monkeypatch):
    monkeypatch.setenv("CRONWRAP_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("CRONWRAP_BUDGET_MAX_SECONDS_PER_DAY", "200")
    cfg = BudgetConfig(enabled=True, max_seconds_per_day=200.0, state_dir=str(tmp_path))
    mgr = BudgetManager(cfg, job_name="testjob")
    return mgr


def test_build_parser_has_subcommands():
    parser = build_parser()
    args = parser.parse_args(["status"])
    assert args.cmd == "status"


def test_cmd_status_output(tmp_mgr, capsys):
    tmp_mgr.record(_result(50.0))
    args = type("A", (), {"job": "testjob"})()
    # Patch manager creation inside cli
    import cronwrap.budget_cli as bcli
    bcli._manager = lambda job: tmp_mgr  # type: ignore[attr-defined]
    cmd_status(args)
    out = capsys.readouterr().out
    assert "50.0" in out
    assert "150.0" in out


def test_cmd_reset_removes_state(tmp_mgr, capsys, tmp_path):
    tmp_mgr.record(_result(30.0))
    state_path = tmp_mgr._state_path()
    assert state_path.exists()

    args = type("A", (), {"job": "testjob"})()
    import cronwrap.budget_cli as bcli
    bcli._manager = lambda job: tmp_mgr  # type: ignore[attr-defined]
    cmd_reset(args)
    assert not state_path.exists()
    out = capsys.readouterr().out
    assert "reset" in out.lower()


def test_cmd_reset_no_state_message(tmp_mgr, capsys):
    args = type("A", (), {"job": "testjob"})()
    import cronwrap.budget_cli as bcli
    bcli._manager = lambda job: tmp_mgr  # type: ignore[attr-defined]
    cmd_reset(args)
    out = capsys.readouterr().out
    assert "No budget state" in out
