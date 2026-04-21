"""Tests for cronwrap.trendline_cli."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cronwrap.trendline import TrendlineConfig, TrendlineManager
from cronwrap.trendline_cli import build_parser, cmd_status, cmd_reset


@pytest.fixture
def tmp_mgr(tmp_path):
    cfg = TrendlineConfig(enabled=True, state_dir=str(tmp_path), window=3, threshold=0.20)
    return TrendlineManager(cfg, job_name="testjob")


def test_build_parser_has_subcommands():
    parser = build_parser()
    args = parser.parse_args(["status", "--job", "myjob"])
    assert args.command == "status"
    assert args.job == "myjob"


def test_build_parser_reset_subcommand():
    parser = build_parser()
    args = parser.parse_args(["reset", "--job", "x"])
    assert args.command == "reset"


def test_cmd_status_no_data(tmp_mgr, capsys):
    args = MagicMock()
    args.job = "testjob"
    with patch("cronwrap.trendline_cli._manager", return_value=tmp_mgr):
        cmd_status(args)
    out = capsys.readouterr().out
    assert "No trendline data" in out


def test_cmd_status_with_data(tmp_mgr, capsys):
    for d in [1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0]:
        r = MagicMock()
        r.duration = d
        tmp_mgr.record(r)
    args = MagicMock()
    args.job = "testjob"
    with patch("cronwrap.trendline_cli._manager", return_value=tmp_mgr):
        cmd_status(args)
    out = capsys.readouterr().out
    assert "testjob" in out
    assert "Direction" in out


def test_cmd_reset_removes_state(tmp_mgr, capsys):
    r = MagicMock()
    r.duration = 1.0
    tmp_mgr.record(r)
    assert tmp_mgr._state_path().exists()
    args = MagicMock()
    args.job = "testjob"
    with patch("cronwrap.trendline_cli._manager", return_value=tmp_mgr):
        cmd_reset(args)
    assert not tmp_mgr._state_path().exists()
    out = capsys.readouterr().out
    assert "reset" in out.lower()


def test_cmd_reset_no_state(tmp_mgr, capsys):
    args = MagicMock()
    args.job = "testjob"
    with patch("cronwrap.trendline_cli._manager", return_value=tmp_mgr):
        cmd_reset(args)
    out = capsys.readouterr().out
    assert "No state found" in out
