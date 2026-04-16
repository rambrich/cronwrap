"""Tests for cronwrap.dashboard."""
import pytest
from unittest.mock import patch, MagicMock
from cronwrap.history import HistoryEntry
from cronwrap.dashboard import render_dashboard, _format_duration, _status_symbol


def _entry(success=True, started_at="2024-01-01T00:00:00", duration=5.0, exit_code=0):
    return HistoryEntry(
        job_name="test_job",
        started_at=started_at,
        duration=duration,
        exit_code=exit_code,
        success=success,
        stdout="",
        stderr="",
    )


def test_format_duration_seconds():
    assert _format_duration(45.5) == "45.5s"


def test_format_duration_minutes():
    assert _format_duration(125.0) == "2m 5s"


def test_status_symbol_success():
    assert _status_symbol(True) == "✓"


def test_status_symbol_failure():
    assert _status_symbol(False) == "✗"


def test_render_empty():
    result = render_dashboard([])
    assert "No history available" in result


def test_render_shows_summary():
    entries = [_entry(success=True), _entry(success=False), _entry(success=True)]
    result = render_dashboard(entries)
    assert "2/3 succeeded" in result


def test_render_with_job_name():
    result = render_dashboard([], job_name="backup")
    assert "backup" in result


def test_render_respects_last_n():
    entries = [_entry() for _ in range(20)]
    result = render_dashboard(entries, last_n=5)
    assert "Last 5 runs" in result


def test_render_shows_exit_code():
    entries = [_entry(success=False, exit_code=1)]
    result = render_dashboard(entries)
    assert "1" in result
