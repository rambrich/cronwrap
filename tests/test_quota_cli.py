"""Tests for cronwrap.quota_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.quota_cli import build_parser, cmd_status, cmd_reset


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write_state(directory: Path, job: str, count: int, limit: int, window: int = 3600) -> None:
    p = directory / f"quota_{job}.json"
    p.write_text(json.dumps({"job": job, "count": count, "limit": limit, "window_seconds": window}))


class _Args:
    def __init__(self, job: str, state_dir: str) -> None:
        self.job = job
        self.state_dir = state_dir


def test_build_parser_has_subcommands() -> None:
    parser = build_parser()
    assert parser is not None


def test_build_parser_status_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["status", "myjob"])
    assert args.command == "status"
    assert args.job == "myjob"


def test_build_parser_reset_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["reset", "myjob"])
    assert args.command == "reset"
    assert args.job == "myjob"


def test_cmd_status_no_state(state_dir: Path, capsys: pytest.CaptureFixture) -> None:
    args = _Args("unknown_job", str(state_dir))
    cmd_status(args)
    out = capsys.readouterr().out
    assert "No quota state" in out


def test_cmd_status_shows_info(state_dir: Path, capsys: pytest.CaptureFixture) -> None:
    _write_state(state_dir, "backup", 3, 10)
    args = _Args("backup", str(state_dir))
    cmd_status(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "3" in out
    assert "10" in out
    assert "ok" in out


def test_cmd_status_shows_exhausted(state_dir: Path, capsys: pytest.CaptureFixture) -> None:
    _write_state(state_dir, "heavy", 10, 10)
    args = _Args("heavy", str(state_dir))
    cmd_status(args)
    out = capsys.readouterr().out
    assert "EXHAUSTED" in out


def test_cmd_reset_removes_file(state_dir: Path, capsys: pytest.CaptureFixture) -> None:
    _write_state(state_dir, "cleanup", 5, 10)
    state_file = state_dir / "quota_cleanup.json"
    assert state_file.exists()
    args = _Args("cleanup", str(state_dir))
    cmd_reset(args)
    assert not state_file.exists()
    out = capsys.readouterr().out
    assert "reset" in out.lower()


def test_cmd_reset_no_state(state_dir: Path, capsys: pytest.CaptureFixture) -> None:
    args = _Args("ghost", str(state_dir))
    cmd_reset(args)
    out = capsys.readouterr().out
    assert "No quota state" in out
