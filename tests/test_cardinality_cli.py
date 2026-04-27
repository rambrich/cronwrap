"""Tests for cronwrap.cardinality_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.cardinality import CardinalityConfig, CardinalityManager
from cronwrap.cardinality_cli import build_parser, cmd_status, cmd_reset
from cronwrap.runner import RunResult


def _result(stdout: str = "out") -> RunResult:
    return RunResult(command="job", exit_code=0, stdout=stdout, stderr="", duration=0.1)


@pytest.fixture
def tmp_mgr(tmp_path):
    cfg = CardinalityConfig(enabled=True, window_seconds=3600, max_unique=5,
                            state_dir=str(tmp_path))
    mgr = CardinalityManager(cfg, job="testjob")
    mgr.record(_result(stdout="alpha"))
    mgr.record(_result(stdout="beta"))
    return mgr, tmp_path


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_build_parser_status_subcommand():
    parser = build_parser()
    args = parser.parse_args(["status", "myjob"])
    assert args.command == "status"
    assert args.job == "myjob"


def test_build_parser_reset_subcommand():
    parser = build_parser()
    args = parser.parse_args(["reset", "myjob"])
    assert args.command == "reset"
    assert args.job == "myjob"


def test_cmd_status_no_state(tmp_path, capsys):
    class Args:
        job = "ghost"
        state_dir = str(tmp_path)
    cmd_status(Args())
    out = capsys.readouterr().out
    assert "No cardinality state" in out


def test_cmd_status_shows_unique_count(tmp_mgr, monkeypatch, capsys):
    mgr, tmp_path = tmp_mgr
    monkeypatch.setenv("CRONWRAP_CARDINALITY_MAX_UNIQUE", "5")

    class Args:
        job = "testjob"
        state_dir = str(tmp_path)
    cmd_status(Args())
    out = capsys.readouterr().out
    assert "Unique count:" in out
    assert "2" in out


def test_cmd_reset_removes_state(tmp_mgr, capsys):
    mgr, tmp_path = tmp_mgr
    state_file = mgr._state_path()
    assert state_file.exists()

    class Args:
        job = "testjob"
        state_dir = str(tmp_path)
    cmd_reset(Args())
    assert not state_file.exists()
    out = capsys.readouterr().out
    assert "reset" in out.lower()
