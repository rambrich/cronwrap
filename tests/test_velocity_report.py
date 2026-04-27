"""Tests for cronwrap.velocity_report."""
import json
from pathlib import Path

import pytest

from cronwrap.velocity_report import (
    VelocitySummary,
    _load_all_states,
    render_report,
    summarize_states,
)


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path


def _write_state(state_dir: Path, job: str, count: int) -> None:
    """Write a fake job state file with `count` timestamps spaced 1 minute apart."""
    import time
    now = time.time()
    timestamps = [now - i * 60 for i in range(count)]
    (state_dir / f"{job}.json").write_text(json.dumps(timestamps))


def test_load_empty_dir(state_dir):
    result = _load_all_states(str(state_dir))
    assert result == []


def test_load_missing_dir(tmp_path):
    result = _load_all_states(str(tmp_path / "nonexistent"))
    assert result == []


def test_load_reads_files(state_dir):
    _write_state(state_dir, "job_a", 3)
    _write_state(state_dir, "job_b", 5)
    result = _load_all_states(str(state_dir))
    jobs = [r["job"] for r in result]
    assert "job_a" in jobs
    assert "job_b" in jobs


def test_summarize_empty(state_dir):
    summary = summarize_states(str(state_dir))
    assert summary.total_jobs == 0
    assert summary.spike_jobs == []
    assert summary.avg_rate_per_hour == 0.0


def test_summarize_counts_jobs(state_dir):
    _write_state(state_dir, "job_a", 2)
    _write_state(state_dir, "job_b", 2)
    summary = summarize_states(str(state_dir))
    assert summary.total_jobs == 2


def test_render_report_contains_header(state_dir):
    _write_state(state_dir, "job_a", 1)
    summary = summarize_states(str(state_dir))
    report = render_report(summary)
    assert "Velocity Report" in report


def test_render_report_shows_avg_rate(state_dir):
    _write_state(state_dir, "job_a", 6)
    summary = summarize_states(str(state_dir))
    report = render_report(summary)
    assert "Avg rate/hour" in report


def test_render_report_no_spikes_shows_none(state_dir):
    _write_state(state_dir, "job_a", 2)
    summary = summarize_states(str(state_dir))
    report = render_report(summary)
    assert "none" in report


def test_render_report_lists_spike_jobs(state_dir):
    """Spike jobs reported by summarize_states should appear in the rendered report."""
    _write_state(state_dir, "job_a", 2)
    # Manually construct a summary with a known spike job to verify rendering.
    summary = VelocitySummary(
        total_jobs=1,
        spike_jobs=["job_a"],
        avg_rate_per_hour=10.0,
    )
    report = render_report(summary)
    assert "job_a" in report
