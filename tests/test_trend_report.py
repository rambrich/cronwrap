"""Tests for cronwrap.trend_report."""
import json
from pathlib import Path

from cronwrap.trend_report import summarize_trends, render_report


def _write_state(state_dir: Path, job: str, history: list) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"{job}.json").write_text(json.dumps(history))


def test_load_empty_dir(tmp_path):
    rows = summarize_trends(str(tmp_path / "trend"))
    assert rows == []


def test_load_missing_dir(tmp_path):
    rows = summarize_trends(str(tmp_path / "nonexistent"))
    assert rows == []


def test_load_reads_files(tmp_path):
    _write_state(tmp_path, "job_a", [1, 1, 0, 1, 1])
    rows = summarize_trends(str(tmp_path), window=5)
    assert len(rows) == 1
    assert rows[0]["job"] == "job_a"


def test_summarize_success_rate(tmp_path):
    _write_state(tmp_path, "jobx", [1, 1, 1, 0, 0])  # 3/5 = 0.6
    rows = summarize_trends(str(tmp_path), window=5)
    assert rows[0]["success_rate"] == 0.6
    assert rows[0]["degrading"] is False


def test_summarize_degrading(tmp_path):
    _write_state(tmp_path, "bad_job", [0, 0, 0, 0, 0])  # 0 %
    rows = summarize_trends(str(tmp_path), window=5)
    assert rows[0]["degrading"] is True


def test_render_report_no_data(tmp_path):
    out = render_report(str(tmp_path / "empty"))
    assert "No trend data" in out


def test_render_report_contains_job(tmp_path):
    _write_state(tmp_path, "myjob", [1, 1, 1])
    out = render_report(str(tmp_path))
    assert "myjob" in out


def test_render_report_shows_degrading(tmp_path):
    _write_state(tmp_path, "badjob", [0, 0, 0, 0, 0])
    out = render_report(str(tmp_path))
    assert "DEGRADING" in out
