"""Tests for cronwrap.sampling_cli."""
import pytest
from unittest.mock import patch

from cronwrap.sampling import SamplingConfig
from cronwrap.sampling_cli import build_parser, cmd_status, cmd_simulate


def test_build_parser_has_subcommands():
    parser = build_parser()
    # Should not raise
    args = parser.parse_args(["status"])
    assert args.command == "status"


def test_build_parser_simulate_defaults():
    parser = build_parser()
    args = parser.parse_args(["simulate"])
    assert args.trials == 100
    assert args.seed is None


def test_cmd_status_output(capsys):
    cfg = SamplingConfig(enabled=True, rate=0.5, seed=7)
    cmd_status(cfg)
    out = capsys.readouterr().out
    assert "True" in out
    assert "0.5000" in out
    assert "50.0%" in out
    assert "7" in out


def test_cmd_status_no_seed(capsys):
    cfg = SamplingConfig(enabled=False, rate=1.0, seed=None)
    cmd_status(cfg)
    out = capsys.readouterr().out
    assert "none" in out


def test_cmd_simulate_output(capsys):
    cfg = SamplingConfig(enabled=True, rate=1.0)
    cmd_simulate(cfg, trials=50, seed=0)
    out = capsys.readouterr().out
    assert "Trials  : 50" in out
    assert "Would run:" in out


def test_cmd_simulate_zero_rate(capsys):
    cfg = SamplingConfig(enabled=True, rate=0.0)
    cmd_simulate(cfg, trials=20, seed=1)
    out = capsys.readouterr().out
    assert "Would run: 0" in out
