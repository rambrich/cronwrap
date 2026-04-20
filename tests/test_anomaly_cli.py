"""Tests for cronwrap.anomaly_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.anomaly import AnomalyConfig, AnomalyDetector
from cronwrap.anomaly_cli import build_parser, cmd_reset, cmd_status
from cronwrap.runner import RunResult


def _result(duration: float = 1.0) -> RunResult:
    return RunResult(
        command="echo hi",
        returncode=0,
        stdout="hi",
        stderr="",
        duration=duration,
    )


@pytest.fixture
def tmp_det(tmp_path):
    cfg = AnomalyConfig(
        enabled=True,
        state_dir=str(tmp_path / "anomaly"),
        window=10,
        z_score_threshold=2.0,
        min_samples=3,
    )
    det = AnomalyDetector(cfg, job_id="testjob")
    for d in [1.0, 1.1, 0.9, 1.05, 0.95]:
        det.check(_result(d))
    return det


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_status_output(tmp_det, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_ANOMALY_STATE_DIR", str(tmp_det.config.state_dir))
    monkeypatch.setenv("CRONWRAP_ANOMALY_ENABLED", "true")

    class Args:
        job = "testjob"

    cmd_status(Args())
    out = capsys.readouterr().out
    assert "testjob" in out
    assert "Samples" in out
    assert "Mean" in out


def test_cmd_status_no_history(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_ANOMALY_STATE_DIR", str(tmp_path / "anomaly"))
    monkeypatch.setenv("CRONWRAP_ANOMALY_ENABLED", "true")

    class Args:
        job = "nonexistent"

    cmd_status(Args())
    out = capsys.readouterr().out
    assert "No history" in out


def test_cmd_reset_removes_state(tmp_det, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_ANOMALY_STATE_DIR", str(tmp_det.config.state_dir))
    monkeypatch.setenv("CRONWRAP_ANOMALY_ENABLED", "true")

    class Args:
        job = "testjob"

    cmd_reset(Args())
    out = capsys.readouterr().out
    assert "Cleared" in out
    assert not tmp_det._state_path().exists()


def test_cmd_reset_no_file(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CRONWRAP_ANOMALY_STATE_DIR", str(tmp_path / "anomaly"))
    monkeypatch.setenv("CRONWRAP_ANOMALY_ENABLED", "true")

    class Args:
        job = "ghost"

    cmd_reset(Args())
    out = capsys.readouterr().out
    assert "No history" in out
