"""Tests for cronwrap.notification_log_report."""
from cronwrap.notification_log import NotificationEntry
from cronwrap.notification_log_report import summarize_entries, render_report


def _entry(**kwargs) -> NotificationEntry:
    defaults = dict(
        job_name="backup",
        channel="email",
        event="failure",
        recipient="ops@example.com",
        success=True,
    )
    defaults.update(kwargs)
    return NotificationEntry(**defaults)


def test_summarize_empty():
    summary = summarize_entries([])
    assert summary["total"] == 0
    assert summary["sent"] == 0
    assert summary["failed"] == 0
    assert summary["by_channel"] == {}


def test_summarize_counts():
    entries = [
        _entry(success=True, channel="email"),
        _entry(success=False, channel="email"),
        _entry(success=True, channel="webhook"),
    ]
    summary = summarize_entries(entries)
    assert summary["total"] == 3
    assert summary["sent"] == 2
    assert summary["failed"] == 1
    assert summary["by_channel"]["email"] == 2
    assert summary["by_channel"]["webhook"] == 1


def test_render_report_contains_header():
    report = render_report([])
    assert "Notification Log Report" in report


def test_render_report_shows_entry_details():
    entries = [_entry(success=True, channel="email", event="failure", recipient="a@b.com")]
    report = render_report(entries)
    assert "email" in report
    assert "a@b.com" in report


def test_render_report_shows_failed_status():
    entries = [_entry(success=False, channel="slack", event="failure", recipient="#ops")]
    report = render_report(entries)
    assert "FAIL" in report
