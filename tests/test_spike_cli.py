"""Tests for cronwrap.spike_cli."""
from __future__ import annotations

import argparse
import json

import pytest

from cronwrap.spike import SpikeConfig, SpikeDetector
from cronwrap.spike_cli import build_parser, cmd_reset, cmd_simulate, cmd_status


@pytest.fixture
def tmp_cfg(tmp_path):
    return SpikeConfig(enabled=True, state_dir=str(tmp_path), window=10, z_threshold=3.0, min_samples=5)


@pytest.fixture
def tmp_det(tmp_cfg):
    return SpikeDetector(tmp_cfg, job="testjob")


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_build_parser_simulate_requires_duration():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["simulate", "--job", "x"])


def test_cmd_status_output(tmp_cfg, capsys):
    args = argparse.Namespace(job="testjob")
    cmd_status(args, tmp_cfg)
    out = capsys.readouterr().out
    assert "Spike detection enabled" in out
    assert "testjob" in out
    assert "Window" in out


def test_cmd_status_shows_mean(tmp_cfg, capsys):
    det = SpikeDetector(tmp_cfg, job="meanjob")
    from cronwrap.runner import RunResult
    for i in range(6):
        det.check(RunResult("echo", 0, "", "", float(i + 1), False))
    args = argparse.Namespace(job="meanjob")
    cmd_status(args, tmp_cfg)
    out = capsys.readouterr().out
    assert "Mean duration" in out


def test_cmd_reset_removes_state(tmp_cfg, tmp_path, capsys):
    det = SpikeDetector(tmp_cfg, job="resetjob")
    from cronwrap.runner import RunResult
    for i in range(6):
        det.check(RunResult("echo", 0, "", "", float(i + 1), False))
    args = argparse.Namespace(job="resetjob")
    cmd_reset(args, tmp_cfg)
    assert not (tmp_path / "resetjob.json").exists()
    out = capsys.readouterr().out
    assert "reset" in out.lower()


def test_cmd_simulate_disabled_prints_message(tmp_cfg, capsys):
    tmp_cfg.enabled = False
    args = argparse.Namespace(job="simjob", duration=5.0)
    cmd_simulate(args, tmp_cfg)
    out = capsys.readouterr().out
    assert "disabled" in out.lower()


def test_cmd_simulate_returns_json(tmp_cfg, capsys):
    args = argparse.Namespace(job="simjob", duration=1.0)
    cmd_simulate(args, tmp_cfg)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "is_spike" in data
    assert "duration" in data
