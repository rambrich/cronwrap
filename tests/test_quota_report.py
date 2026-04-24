"""Tests for cronwrap.quota_report."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.quota_report import (
    _load_all_states,
    summarize_states,
    render_report,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write_state(directory: Path, job: str, count: int, limit: int, window: int = 3600) -> None:
    p = directory / f"quota_{job}.json"
    p.write_text(json.dumps({"job": job, "count": count, "limit": limit, "window_seconds": window}))


def test_load_empty_dir(state_dir: Path) -> None:
    assert _load_all_states(str(state_dir)) == []


def test_load_missing_dir(tmp_path: Path) -> None:
    missing = str(tmp_path / "no_such_dir")
    assert _load_all_states(missing) == []


def test_load_reads_files(state_dir: Path) -> None:
    _write_state(state_dir, "backup", 3, 10)
    _write_state(state_dir, "cleanup", 10, 10)
    states = _load_all_states(str(state_dir))
    assert len(states) == 2
    jobs = {s["job"] for s in states}
    assert jobs == {"backup", "cleanup"}


def test_summarize_empty() -> None:
    result = summarize_states([])
    assert result["total_jobs"] == 0
    assert result["exhausted"] == 0
    assert result["within_quota"] == 0


def test_summarize_counts(state_dir: Path) -> None:
    states = [
        {"job": "a", "count": 5, "limit": 10},
        {"job": "b", "count": 10, "limit": 10},
        {"job": "c", "count": 0, "limit": 5},
    ]
    result = summarize_states(states)
    assert result["total_jobs"] == 3
    assert result["exhausted"] == 1
    assert result["within_quota"] == 2


def test_render_report_contains_header(state_dir: Path) -> None:
    _write_state(state_dir, "myjob", 2, 5)
    states = _load_all_states(str(state_dir))
    report = render_report(states)
    assert "Quota Report" in report
    assert "myjob" in report


def test_render_report_shows_exhausted(state_dir: Path) -> None:
    _write_state(state_dir, "heavy", 10, 10)
    states = _load_all_states(str(state_dir))
    report = render_report(states)
    assert "EXHAUSTED" in report


def test_render_report_shows_ok(state_dir: Path) -> None:
    _write_state(state_dir, "light", 1, 100)
    states = _load_all_states(str(state_dir))
    report = render_report(states)
    assert "ok" in report
