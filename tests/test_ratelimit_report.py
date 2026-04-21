"""Tests for ratelimit_report module."""
from __future__ import annotations

import json
import os
import pytest

from cronwrap.ratelimit_report import (
    _load_all_states,
    summarize_states,
    render_report,
    RateLimitSummary,
)


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


def _write_state(state_dir, job, count, blocked=False):
    os.makedirs(state_dir, exist_ok=True)
    fpath = os.path.join(state_dir, f"{job}.ratelimit.json")
    with open(fpath, "w") as f:
        json.dump({"count": count, "blocked": blocked}, f)


def test_load_all_states_empty_dir(state_dir):
    states = _load_all_states(state_dir)
    assert states == []


def test_load_all_states_missing_dir():
    states = _load_all_states("/nonexistent/path/xyz")
    assert states == []


def test_load_all_states_reads_files(state_dir):
    _write_state(state_dir, "myjob", 5, blocked=False)
    states = _load_all_states(state_dir)
    assert len(states) == 1
    assert states[0]["_job"] == "myjob"
    assert states[0]["count"] == 5


def test_load_all_states_ignores_other_files(state_dir):
    _write_state(state_dir, "myjob", 3)
    with open(os.path.join(state_dir, "other.json"), "w") as f:
        f.write("{}")
    states = _load_all_states(state_dir)
    assert len(states) == 1


def test_summarize_empty():
    summary = summarize_states([])
    assert summary.total_jobs == 0
    assert summary.active_jobs == 0
    assert summary.total_requests == 0
    assert summary.blocked_jobs == []


def test_summarize_counts(state_dir):
    states = [
        {"_job": "a", "count": 10, "blocked": False},
        {"_job": "b", "count": 0, "blocked": False},
        {"_job": "c", "count": 5, "blocked": True},
    ]
    summary = summarize_states(states)
    assert summary.total_jobs == 3
    assert summary.active_jobs == 2
    assert summary.total_requests == 15
    assert summary.blocked_jobs == ["c"]


def test_render_report_contains_header():
    summary = RateLimitSummary(3, 2, 15, ["c"])
    report = render_report(summary)
    assert "Rate Limit Report" in report
    assert "3" in report
    assert "15" in report
    assert "c" in report


def test_render_report_no_blocked_jobs():
    summary = RateLimitSummary(2, 1, 8, [])
    report = render_report(summary)
    assert "Blocked job list" not in report
