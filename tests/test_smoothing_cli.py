"""Tests for cronwrap.smoothing_cli."""
import argparse
import pytest
from unittest.mock import MagicMock, patch
from cronwrap.smoothing import SmoothingConfig, SmoothingManager
from cronwrap.smoothing_cli import build_parser, cmd_status, cmd_reset, cmd_list


@pytest.fixture
def tmp_mgr(tmp_path):
    cfg = SmoothingConfig(enabled=True, alpha=0.5, state_dir=str(tmp_path))
    return SmoothingManager(cfg), tmp_path


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


def test_build_parser_list_subcommand():
    parser = build_parser()
    args = parser.parse_args(["list"])
    assert args.command == "list"


def test_cmd_status_no_data(tmp_mgr, capsys):
    mgr, tmp_path = tmp_mgr
    args = argparse.Namespace(job="ghost", state_dir=str(tmp_path))
    with patch("cronwrap.smoothing_cli._manager", return_value=mgr):
        cmd_status(args)
    out = capsys.readouterr().out
    assert "No smoothing data" in out


def test_cmd_status_shows_value(tmp_mgr, capsys):
    mgr, tmp_path = tmp_mgr
    mgr.update("myjob", 12.5)
    args = argparse.Namespace(job="myjob", state_dir=str(tmp_path))
    with patch("cronwrap.smoothing_cli._manager", return_value=mgr):
        cmd_status(args)
    out = capsys.readouterr().out
    assert "myjob" in out
    assert "12.5000" in out


def test_cmd_reset_clears_state(tmp_mgr, capsys):
    mgr, tmp_path = tmp_mgr
    mgr.update("job1", 5.0)
    assert mgr.current("job1") is not None
    args = argparse.Namespace(job="job1", state_dir=str(tmp_path))
    with patch("cronwrap.smoothing_cli._manager", return_value=mgr):
        cmd_reset(args)
    assert mgr.current("job1") is None
    out = capsys.readouterr().out
    assert "reset" in out.lower()


def test_cmd_list_empty(tmp_path, capsys):
    args = argparse.Namespace(state_dir=str(tmp_path))
    with patch("cronwrap.smoothing_cli.SmoothingConfig.from_env",
               return_value=SmoothingConfig(enabled=True, state_dir=str(tmp_path))):
        cmd_list(args)
    out = capsys.readouterr().out
    assert "No smoothing state found" in out


def test_cmd_list_shows_jobs(tmp_path, capsys):
    cfg = SmoothingConfig(enabled=True, alpha=0.5, state_dir=str(tmp_path))
    mgr = SmoothingManager(cfg)
    mgr.update("alpha_job", 3.0)
    mgr.update("beta_job", 7.0)
    args = argparse.Namespace(state_dir=str(tmp_path))
    with patch("cronwrap.smoothing_cli.SmoothingConfig.from_env", return_value=cfg):
        cmd_list(args)
    out = capsys.readouterr().out
    assert "alpha_job" in out
    assert "beta_job" in out
