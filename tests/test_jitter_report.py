"""Tests for cronwrap.jitter_report."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.jitter_report import (
    JitterSummary,
    _load_all_samples,
    render_report,
    summarize_samples,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write_state(state_dir: Path, job: str, samples: list) -> None:
    path = state_dir / f"jitter_{job}.json"
    path.write_text(json.dumps({"job": job, "samples": samples}))


def test_load_empty_dir(state_dir: Path) -> None:
    result = _load_all_samples(state_dir)
    assert result == {}


def test_load_missing_dir(tmp_path: Path) -> None:
    result = _load_all_samples(tmp_path / "nonexistent")
    assert result == {}


def test_load_reads_files(state_dir: Path) -> None:
    _write_state(state_dir, "backup", [1.0, 2.0, 3.0])
    result = _load_all_samples(state_dir)
    assert "backup" in result
    assert result["backup"] == [1.0, 2.0, 3.0]


def test_summarize_empty(state_dir: Path) -> None:
    summaries = summarize_samples(state_dir)
    assert summaries == []


def test_summarize_single_sample(state_dir: Path) -> None:
    _write_state(state_dir, "myjob", [5.0])
    summaries = summarize_samples(state_dir)
    assert len(summaries) == 1
    s = summaries[0]
    assert s.job_name == "myjob"
    assert s.sample_count == 1
    assert s.min_seconds == 5.0
    assert s.max_seconds == 5.0
    assert s.mean_seconds == 5.0
    assert s.stddev_seconds == 0.0


def test_summarize_multiple_samples(state_dir: Path) -> None:
    _write_state(state_dir, "job1", [1.0, 3.0, 5.0])
    summaries = summarize_samples(state_dir)
    s = summaries[0]
    assert s.min_seconds == pytest.approx(1.0)
    assert s.max_seconds == pytest.approx(5.0)
    assert s.mean_seconds == pytest.approx(3.0)
    assert s.stddev_seconds > 0.0


def test_render_report_empty() -> None:
    output = render_report([])
    assert "No jitter data" in output


def test_render_report_contains_job_name(state_dir: Path) -> None:
    _write_state(state_dir, "cleanup", [0.5, 1.5])
    summaries = summarize_samples(state_dir)
    output = render_report(summaries)
    assert "cleanup" in output
    assert "Jitter Report" in output
    assert "Mean" in output
