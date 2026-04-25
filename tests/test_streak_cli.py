"""Tests for cronwrap.streak_cli."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from cronwrap.streak import StreakConfig, StreakManager, StreakState
from cronwrap.streak_cli import build_parser, cmd_list, cmd_reset, cmd_status
from cronwrap.runner import RunResult


def _result(rc: int) -> RunResult:
    return RunResult(command="echo hi", returncode=rc, stdout="", stderr="", duration=0.5)


@pytest.fixture()
def tmp_mgr(tmp_path):
    cfg = StreakConfig(enabled=True, state_dir=str(tmp_path), alert_on_failure_streak=3)
    return StreakManager(cfg, "test-job")


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


def test_cmd_status_no_state(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_STREAK_STATE_DIR", str(tmp_path))
    args = argparse.Namespace(job="ghost-job")
    cmd_status(args)
    out = capsys.readouterr().out
    assert "No streak state found" in out


def test_cmd_status_shows_state(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_STREAK_STATE_DIR", str(tmp_path))
    cfg = StreakConfig(enabled=True, state_dir=str(tmp_path))
    mgr = StreakManager(cfg, "test-job")
    mgr.record(_result(1))
    mgr.record(_result(1))
    args = argparse.Namespace(job="test-job")
    cmd_status(args)
    out = capsys.readouterr().out
    assert "test-job" in out
    assert "failure" in out
    assert "2" in out


def test_cmd_reset_removes_state(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_STREAK_STATE_DIR", str(tmp_path))
    cfg = StreakConfig(enabled=True, state_dir=str(tmp_path))
    mgr = StreakManager(cfg, "test-job")
    mgr.record(_result(0))
    assert mgr._state_path().exists()
    args = argparse.Namespace(job="test-job")
    cmd_reset(args)
    assert not mgr._state_path().exists()
    out = capsys.readouterr().out
    assert "reset" in out


def test_cmd_list_empty(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_STREAK_STATE_DIR", str(tmp_path))
    args = argparse.Namespace()
    cmd_list(args)
    out = capsys.readouterr().out
    assert "No tracked jobs" in out


def test_cmd_list_shows_jobs(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_STREAK_STATE_DIR", str(tmp_path))
    cfg = StreakConfig(enabled=True, state_dir=str(tmp_path))
    for job in ("job-a", "job-b"):
        mgr = StreakManager(cfg, job)
        mgr.record(_result(0))
    args = argparse.Namespace()
    cmd_list(args)
    out = capsys.readouterr().out
    assert "job-a" in out
    assert "job-b" in out
