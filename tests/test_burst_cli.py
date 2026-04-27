"""Tests for cronwrap.burst_cli."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pytest

from cronwrap.burst import BurstConfig, BurstManager
from cronwrap.burst_cli import build_parser, cmd_status, cmd_reset


@pytest.fixture
def tmp_cfg(tmp_path):
    return BurstConfig(
        enabled=True,
        window_seconds=60,
        max_runs=3,
        state_dir=str(tmp_path / "burst"),
    )


@pytest.fixture
def tmp_mgr(tmp_cfg):
    mgr = BurstManager(config=tmp_cfg, job="testjob")
    now = time.time()
    mgr.record(now=now)
    mgr.record(now=now + 1)
    return mgr


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


def test_cmd_status_output(tmp_cfg, tmp_mgr, capsys):
    args = argparse.Namespace(job="testjob")
    cmd_status(args, tmp_cfg)
    out = capsys.readouterr().out
    assert "testjob" in out
    assert "OK" in out


def test_cmd_status_shows_burst(tmp_cfg, capsys):
    mgr = BurstManager(config=tmp_cfg, job="burstjob")
    now = time.time()
    for i in range(5):
        mgr.record(now=now + i)
    args = argparse.Namespace(job="burstjob")
    cmd_status(args, tmp_cfg)
    out = capsys.readouterr().out
    assert "BURST" in out


def test_cmd_reset_clears_state(tmp_cfg, tmp_mgr, capsys):
    args = argparse.Namespace(job="testjob")
    cmd_reset(args, tmp_cfg)
    out = capsys.readouterr().out
    assert "reset" in out.lower()
    mgr2 = BurstManager(config=tmp_cfg, job="testjob")
    assert len(mgr2._timestamps) == 0


def test_cmd_status_disabled(tmp_path, capsys):
    cfg = BurstConfig(enabled=False, state_dir=str(tmp_path))
    args = argparse.Namespace(job="myjob")
    cmd_status(args, cfg)
    out = capsys.readouterr().out
    assert "disabled" in out.lower()
