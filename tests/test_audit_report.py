"""Tests for cronwrap.audit_report."""
from cronwrap.audit import AuditEntry
from cronwrap.audit_report import render_report, summarize_entries


def _entry(command="echo hi", success=True, duration=1.0, exit_code=0):
    return AuditEntry(
        timestamp="2024-01-01T00:00:00+00:00",
        command=command,
        exit_code=exit_code,
        duration=duration,
        success=success,
    )


def test_summarize_empty():
    result = summarize_entries([])
    assert result["total"] == 0
    assert result["avg_duration"] == 0.0


def test_summarize_counts():
    entries = [_entry(success=True), _entry(success=False), _entry(success=True)]
    result = summarize_entries(entries)
    assert result["total"] == 3
    assert result["successes"] == 2
    assert result["failures"] == 1


def test_summarize_avg_duration():
    entries = [_entry(duration=2.0), _entry(duration=4.0)]
    result = summarize_entries(entries)
    assert result["avg_duration"] == 3.0


def test_summarize_command_counts():
    entries = [_entry(command="a"), _entry(command="b"), _entry(command="a")]
    result = summarize_entries(entries)
    assert result["commands"]["a"] == 2
    assert result["commands"]["b"] == 1


def test_render_report_contains_totals():
    entries = [_entry(success=True), _entry(success=False)]
    report = render_report(entries)
    assert "Total runs" in report
    assert "Successes" in report
    assert "Failures" in report


def test_render_report_lists_commands():
    entries = [_entry(command="my-job"), _entry(command="my-job")]
    report = render_report(entries)
    assert "my-job" in report
    assert "2x" in report
