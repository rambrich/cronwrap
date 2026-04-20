"""Tests for cronwrap.sla_report."""
from __future__ import annotations

from cronwrap.sla import SLAViolation
from cronwrap.sla_report import render_report, summarize_violations


def _violation(reason: str = "max_duration_seconds exceeded", job: str = "myjob") -> SLAViolation:
    return SLAViolation(
        job_name=job,
        reason=reason,
        value=10.0,
        threshold=5.0,
        timestamp=1_700_000_000.0,
    )


def test_summarize_empty():
    result = summarize_violations([])
    assert result["total"] == 0
    assert result["by_reason"] == {}
    assert result["jobs"] == []


def test_summarize_counts():
    violations = [
        _violation(reason="max_duration_seconds exceeded", job="job_a"),
        _violation(reason="max_failures_per_day exceeded", job="job_b"),
        _violation(reason="max_duration_seconds exceeded", job="job_a"),
    ]
    result = summarize_violations(violations)
    assert result["total"] == 3
    assert result["by_reason"]["max_duration_seconds exceeded"] == 2
    assert result["by_reason"]["max_failures_per_day exceeded"] == 1
    assert set(result["jobs"]) == {"job_a", "job_b"}


def test_render_report_contains_header():
    report = render_report([])
    assert "SLA Violation Report" in report
    assert "Total violations" in report


def test_render_report_shows_violation_details():
    v = _violation()
    report = render_report([v])
    assert "myjob" in report
    assert "max_duration_seconds exceeded" in report
    assert "10.00" in report
    assert "5.00" in report


def test_render_report_no_violations_message():
    report = render_report([])
    assert "0" in report
    assert "none" in report
