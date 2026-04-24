"""Tests for cronwrap.cadence_cli."""
from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from cronwrap.cadence_cli import build_parser, cmd_reset, cmd_status


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


def _write_state(state_dir: str, job_id: str, ts: float) -> None:
    p = Path(state_dir) / f"{job_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"last_run_ts": ts}))


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_build_parser_status_defaults():
    parser = build_parser()
    args = parser.parse_args(["status"])
    assert args.job_id == "default"
    assert args.command == "status"


def test_build_parser_reset_defaults():
    parser = build_parser()
    args = parser.parse_args(["reset"])
    assert args.command == "reset"


def test_cmd_status_no_state(state_dir, capsys):
    args = SimpleNamespace(job_id="myjob", state_dir=state_dir)
    cmd_status(args)
    out = capsys.readouterr().out
    assert "No cadence state" in out


def test_cmd_status_shows_last_run(state_dir, capsys):
    ts = time.time() - 1800
    _write_state(state_dir, "myjob", ts)
    args = SimpleNamespace(job_id="myjob", state_dir=state_dir)
    cmd_status(args)
    out = capsys.readouterr().out
    assert "Last run" in out
    assert "myjob" in out


def test_cmd_reset_removes_state(state_dir, capsys):
    _write_state(state_dir, "myjob", time.time())
    p = Path(state_dir) / "myjob.json"
    assert p.exists()
    args = SimpleNamespace(job_id="myjob", state_dir=state_dir)
    cmd_reset(args)
    assert not p.exists()
    out = capsys.readouterr().out
    assert "reset" in out.lower()


def test_cmd_reset_noop_when_no_state(state_dir, capsys):
    args = SimpleNamespace(job_id="nonexistent", state_dir=state_dir)
    cmd_reset(args)  # should not raise
    out = capsys.readouterr().out
    assert "reset" in out.lower()
