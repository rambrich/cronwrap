"""Tests for cronwrap.drift_report."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.drift_report import load_drift_results, summarize_results, render_report


def _write_entry(state_dir: Path, job: str, drift: float, warn: bool, crit: bool) -> None:
    data = {
        "job": job,
        "expected_at": 1000.0,
        "actual_at": 1000.0 + drift,
        "drift_seconds": drift,
        "is_warning": warn,
        "is_critical": crit,
    }
    (state_dir / f"{job}.json").write_text(json.dumps(data))


def test_load_empty_dir(tmp_path):
    results = load_drift_results(str(tmp_path))
    assert results == []


def test_load_missing_dir(tmp_path):
    results = load_drift_results(str(tmp_path / "nonexistent"))
    assert results == []


def test_load_reads_files(tmp_path):
    _write_entry(tmp_path, "job_a", 10.0, False, False)
    _write_entry(tmp_path, "job_b", 90.0, True, False)
    results = load_drift_results(str(tmp_path))
    assert len(results) == 2


def test_summarize_empty():
    summary = summarize_results([])
    assert summary["total"] == 0
    assert summary["warnings"] == 0
    assert summary["criticals"] == 0
    assert summary["avg_drift_seconds"] == 0.0
    assert summary["max_drift_seconds"] == 0.0


def test_summarize_counts(tmp_path):
    entries = [
        {"drift_seconds": 10.0, "is_warning": False, "is_critical": False},
        {"drift_seconds": 80.0, "is_warning": True, "is_critical": False},
        {"drift_seconds": 400.0, "is_warning": True, "is_critical": True},
    ]
    summary = summarize_results(entries)
    assert summary["total"] == 3
    assert summary["warnings"] == 2
    assert summary["criticals"] == 1


def test_summarize_avg_and_max():
    entries = [
        {"drift_seconds": 20.0, "is_warning": False, "is_critical": False},
        {"drift_seconds": 40.0, "is_warning": False, "is_critical": False},
    ]
    summary = summarize_results(entries)
    assert summary["avg_drift_seconds"] == pytest.approx(30.0)
    assert summary["max_drift_seconds"] == pytest.approx(40.0)


def test_render_report_contains_header(tmp_path):
    _write_entry(tmp_path, "job_x", 5.0, False, False)
    results = load_drift_results(str(tmp_path))
    report = render_report(results)
    assert "Drift Report" in report
    assert "job_x" in report


def test_render_report_empty():
    report = render_report([])
    assert "Drift Report" in report
    assert "Total jobs tracked" in report
