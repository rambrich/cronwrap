"""Tests for cronwrap.latency_cli."""
import json
import pytest
from unittest.mock import MagicMock, patch

from cronwrap.latency import LatencyConfig, LatencyManager
from cronwrap.latency_cli import build_parser, cmd_status, cmd_reset


@pytest.fixture
def tmp_mgr(tmp_path):
    cfg = LatencyConfig(
        enabled=True,
        warn_seconds=10.0,
        crit_seconds=30.0,
        state_dir=str(tmp_path),
        window=10,
    )
    return LatencyManager(cfg, "testjob")


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


def test_cmd_status_no_data(tmp_mgr, capsys):
    args = MagicMock()
    args.job = "testjob"
    with patch("cronwrap.latency_cli._manager", return_value=tmp_mgr):
        cmd_status(args)
    out = capsys.readouterr().out
    assert "No latency data" in out


def test_cmd_status_with_data(tmp_mgr, capsys):
    from unittest.mock import MagicMock as MM
    from cronwrap.runner import RunResult
    r = MM(spec=RunResult)
    r.duration = 7.5
    r.exit_code = 0
    r.stdout = ""
    r.stderr = ""
    tmp_mgr.record(r)
    args = MagicMock()
    args.job = "testjob"
    with patch("cronwrap.latency_cli._manager", return_value=tmp_mgr):
        cmd_status(args)
    out = capsys.readouterr().out
    assert "7.50" in out
    assert "Samples" in out


def test_cmd_reset_clears_state(tmp_mgr, capsys):
    from unittest.mock import MagicMock as MM
    from cronwrap.runner import RunResult
    r = MM(spec=RunResult)
    r.duration = 5.0
    r.exit_code = 0
    r.stdout = ""
    r.stderr = ""
    tmp_mgr.record(r)
    args = MagicMock()
    args.job = "testjob"
    with patch("cronwrap.latency_cli._manager", return_value=tmp_mgr):
        cmd_reset(args)
    out = capsys.readouterr().out
    assert "cleared" in out
    assert tmp_mgr._load_samples() == []
