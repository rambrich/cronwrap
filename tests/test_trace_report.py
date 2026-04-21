"""Tests for cronwrap.trace_report"""
from cronwrap.trace_report import summarize_traces, render_trace_report


def _entry(success=True, duration=1.0, command="echo", trace_id="abc-123"):
    return {"trace_id": trace_id, "command": command, "success": success, "duration": duration}


def test_summarize_empty():
    s = summarize_traces([])
    assert s["total"] == 0
    assert s["avg_duration"] == 0.0


def test_summarize_counts():
    entries = [_entry(True), _entry(False), _entry(True)]
    s = summarize_traces(entries)
    assert s["total"] == 3
    assert s["successes"] == 2
    assert s["failures"] == 1


def test_summarize_avg_duration():
    entries = [_entry(duration=2.0), _entry(duration=4.0)]
    s = summarize_traces(entries)
    assert s["avg_duration"] == 3.0


def test_summarize_all_failures():
    """Ensure failure-only traces are counted correctly with zero successes."""
    entries = [_entry(success=False), _entry(success=False)]
    s = summarize_traces(entries)
    assert s["total"] == 2
    assert s["successes"] == 0
    assert s["failures"] == 2


def test_render_report_contains_header():
    report = render_trace_report([_entry()])
    assert "Trace Report" in report
    assert "Successes" in report


def test_render_report_shows_checkmark():
    report = render_trace_report([_entry(success=True)])
    assert "✓" in report


def test_render_report_shows_cross():
    report = render_trace_report([_entry(success=False)])
    assert "✗" in report


def test_render_report_includes_trace_id():
    """Ensure each entry's trace_id appears in the rendered report."""
    trace_id = "xyz-789"
    report = render_trace_report([_entry(trace_id=trace_id)])
    assert trace_id in report
