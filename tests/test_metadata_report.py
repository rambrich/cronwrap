"""Tests for cronwrap.metadata_report."""
import pytest
from cronwrap.metadata import RunMetadata
from cronwrap.metadata_report import summarize_metadata, render_report


def _entry(hostname="host1", user="alice", extra=None):
    return RunMetadata(hostname=hostname, user=user, extra=extra or {})


def test_summarize_empty():
    result = summarize_metadata([])
    assert result["total"] == 0
    assert result["hostnames"] == {}
    assert result["users"] == {}
    assert result["extra_keys"] == []


def test_summarize_counts_hostnames():
    entries = [_entry(hostname="h1"), _entry(hostname="h1"), _entry(hostname="h2")]
    result = summarize_metadata(entries)
    assert result["hostnames"] == {"h1": 2, "h2": 1}


def test_summarize_counts_users():
    entries = [_entry(user="alice"), _entry(user="bob"), _entry(user="alice")]
    result = summarize_metadata(entries)
    assert result["users"] == {"alice": 2, "bob": 1}


def test_summarize_extra_keys():
    entries = [
        _entry(extra={"env": "prod", "region": "us"}),
        _entry(extra={"env": "staging"}),
    ]
    result = summarize_metadata(entries)
    assert set(result["extra_keys"]) == {"env", "region"}


def test_summarize_total():
    entries = [_entry(), _entry(), _entry()]
    result = summarize_metadata(entries)
    assert result["total"] == 3


def test_render_report_contains_header():
    entries = [_entry()]
    summary = summarize_metadata(entries)
    report = render_report(summary)
    assert "Metadata Report" in report


def test_render_report_shows_hostname():
    entries = [_entry(hostname="myhost")]
    summary = summarize_metadata(entries)
    report = render_report(summary)
    assert "myhost" in report


def test_render_report_shows_user():
    entries = [_entry(user="bob")]
    summary = summarize_metadata(entries)
    report = render_report(summary)
    assert "bob" in report


def test_render_report_shows_extra_keys():
    entries = [_entry(extra={"env": "prod"})]
    summary = summarize_metadata(entries)
    report = render_report(summary)
    assert "env" in report


def test_render_report_empty_no_crash():
    summary = summarize_metadata([])
    report = render_report(summary)
    assert "0" in report
