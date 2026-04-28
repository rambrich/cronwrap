"""Tests for cronwrap.jitter_cli."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cronwrap.jitter_cli import build_parser, cmd_report, cmd_simulate, cmd_status


def test_build_parser_has_subcommands() -> None:
    parser = build_parser()
    assert parser is not None


def test_build_parser_simulate_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["simulate"])
    assert args.runs == 5


def test_build_parser_report_default_state_dir() -> None:
    parser = build_parser()
    args = parser.parse_args(["report"])
    assert "cronwrap" in args.state_dir


def test_cmd_status_output(capsys: pytest.CaptureFixture) -> None:
    args = SimpleNamespace()
    cmd_status(args)
    captured = capsys.readouterr()
    assert "Jitter enabled" in captured.out
    assert "Max seconds" in captured.out


def test_cmd_report_no_data(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = SimpleNamespace(state_dir=str(tmp_path))
    cmd_report(args)
    captured = capsys.readouterr()
    assert "No jitter data" in captured.out


def test_cmd_report_with_data(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    state_file = tmp_path / "jitter_myjob.json"
    state_file.write_text(json.dumps({"job": "myjob", "samples": [1.0, 2.0, 3.0]}))
    args = SimpleNamespace(state_dir=str(tmp_path))
    cmd_report(args)
    captured = capsys.readouterr()
    assert "myjob" in captured.out
    assert "Jitter Report" in captured.out


def test_cmd_simulate_disabled(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("CRONWRAP_JITTER_ENABLED", "false")
    args = SimpleNamespace(runs=3)
    cmd_simulate(args)
    captured = capsys.readouterr()
    assert "disabled" in captured.out.lower()


def test_cmd_simulate_enabled(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setenv("CRONWRAP_JITTER_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_JITTER_MAX_SECONDS", "2.0")
    monkeypatch.setenv("CRONWRAP_JITTER_SEED", "42")
    args = SimpleNamespace(runs=3)
    cmd_simulate(args)
    captured = capsys.readouterr()
    assert "[1]" in captured.out
    assert "[3]" in captured.out
