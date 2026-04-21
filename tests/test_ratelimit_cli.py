"""Tests for ratelimit_cli module."""
from __future__ import annotations

import json
import os
import pytest

from cronwrap.ratelimit_cli import build_parser, cmd_status, cmd_reset, cmd_report


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CRONWRAP_STATE_DIR", str(tmp_path))
    return str(tmp_path)


def _write_state(state_dir, job, count, blocked=False):
    fpath = os.path.join(state_dir, f"{job}.ratelimit.json")
    with open(fpath, "w") as f:
        json.dump({"count": count, "blocked": blocked}, f)


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_build_parser_reset_requires_job():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["reset"])


def test_cmd_status_no_state(state_dir, capsys):
    args = build_parser().parse_args(["status"])
    cmd_status(args)
    out = capsys.readouterr().out
    assert "No rate limit state found" in out


def test_cmd_status_shows_jobs(state_dir, capsys):
    _write_state(state_dir, "backup", 7, blocked=False)
    args = build_parser().parse_args(["status"])
    cmd_status(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "count=7" in out
    assert "ok" in out


def test_cmd_status_shows_blocked(state_dir, capsys):
    _write_state(state_dir, "sync", 100, blocked=True)
    args = build_parser().parse_args(["status"])
    cmd_status(args)
    out = capsys.readouterr().out
    assert "BLOCKED" in out


def test_cmd_reset_removes_file(state_dir, capsys):
    _write_state(state_dir, "myjob", 3)
    fpath = os.path.join(state_dir, "myjob.ratelimit.json")
    assert os.path.exists(fpath)
    args = build_parser().parse_args(["reset", "myjob"])
    cmd_reset(args)
    assert not os.path.exists(fpath)
    out = capsys.readouterr().out
    assert "myjob" in out


def test_cmd_reset_missing_job(state_dir, capsys):
    args = build_parser().parse_args(["reset", "ghost"])
    cmd_reset(args)
    out = capsys.readouterr().out
    assert "No state found" in out


def test_cmd_report_prints_output(state_dir, capsys):
    _write_state(state_dir, "jobA", 4)
    args = build_parser().parse_args(["report"])
    cmd_report(args)
    out = capsys.readouterr().out
    assert "Rate Limit Report" in out
