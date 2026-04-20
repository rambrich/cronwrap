"""Tests for cronwrap.eventlog."""
from __future__ import annotations

import json
import os
import time

import pytest

from cronwrap.eventlog import EventEntry, EventLogConfig, EventLogger
from cronwrap.runner import RunResult


def _result(exit_code: int = 0, duration: float = 1.0) -> RunResult:
    return RunResult(
        command="echo hello",
        exit_code=exit_code,
        stdout="hello",
        stderr="",
        duration=duration,
    )


@pytest.fixture()
def tmp_config(tmp_path):
    return EventLogConfig(enabled=True, log_dir=str(tmp_path / "events"), max_events=10)


def test_config_disabled_by_default():
    cfg = EventLogConfig()
    assert cfg.enabled is False


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_EVENTLOG_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_EVENTLOG_DIR", "/tmp/el")
    monkeypatch.setenv("CRONWRAP_EVENTLOG_MAX_EVENTS", "100")
    cfg = EventLogConfig.from_env()
    assert cfg.enabled is True
    assert cfg.log_dir == "/tmp/el"
    assert cfg.max_events == 100


def test_record_returns_none_when_disabled():
    mgr = EventLogger(EventLogConfig(enabled=False))
    assert mgr.record("start", _result()) is None


def test_record_writes_entry(tmp_config, tmp_path):
    mgr = EventLogger(tmp_config)
    result = _result(exit_code=0, duration=2.5)
    entry = mgr.record("success", result, detail="ok")
    assert entry is not None
    assert entry.event == "success"
    assert entry.exit_code == 0
    assert entry.duration == pytest.approx(2.5)
    assert entry.detail == "ok"


def test_record_persists_to_disk(tmp_config):
    mgr = EventLogger(tmp_config)
    mgr.record("start", _result())
    entries = mgr.load("echo hello")
    assert len(entries) == 1
    assert entries[0].event == "start"


def test_load_returns_empty_when_disabled():
    mgr = EventLogger(EventLogConfig(enabled=False))
    assert mgr.load("echo hello") == []


def test_load_returns_empty_when_no_file(tmp_config):
    mgr = EventLogger(tmp_config)
    assert mgr.load("nonexistent command") == []


def test_max_events_truncates_old_entries(tmp_config):
    tmp_config.max_events = 3
    mgr = EventLogger(tmp_config)
    for i in range(5):
        mgr.record(f"event_{i}", _result())
    entries = mgr.load("echo hello")
    assert len(entries) == 3
    assert entries[-1].event == "event_4"


def test_entry_to_dict():
    e = EventEntry(event="failure", command="ls", exit_code=1, duration=0.5, detail="err")
    d = e.to_dict()
    assert d["event"] == "failure"
    assert d["exit_code"] == 1
    assert d["duration"] == pytest.approx(0.5)
