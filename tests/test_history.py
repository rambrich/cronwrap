"""Tests for cronwrap.history module."""

import json
from pathlib import Path

import pytest

from cronwrap.history import HistoryConfig, HistoryStore
from cronwrap.runner import RunResult


def _make_result(success: bool = True, exit_code: int = 0) -> RunResult:
    return RunResult(
        command="echo hello",
        success=success,
        exit_code=exit_code,
        stdout="hello",
        stderr="",
        duration=1.23,
        attempts=1,
    )


def test_history_config_disabled_by_default():
    config = HistoryConfig()
    assert config.enabled is False


def test_history_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_HISTORY_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_HISTORY_FILE", "/tmp/test_history.json")
    monkeypatch.setenv("CRONWRAP_HISTORY_MAX_ENTRIES", "50")
    config = HistoryConfig.from_env()
    assert config.enabled is True
    assert config.history_file == "/tmp/test_history.json"
    assert config.max_entries == 50


def test_record_returns_none_when_disabled():
    config = HistoryConfig(enabled=False)
    store = HistoryStore(config)
    result = store.record("my-job", _make_result())
    assert result is None


def test_record_writes_entry(tmp_path):
    history_file = str(tmp_path / "history.json")
    config = HistoryConfig(enabled=True, history_file=history_file)
    store = HistoryStore(config)

    entry = store.record("my-job", _make_result(success=True, exit_code=0))

    assert entry is not None
    assert entry.job_name == "my-job"
    assert entry.success is True
    assert entry.exit_code == 0
    assert entry.command == "echo hello"

    raw = json.loads(Path(history_file).read_text())
    assert len(raw) == 1
    assert raw[0]["job_name"] == "my-job"


def test_record_respects_max_entries(tmp_path):
    history_file = str(tmp_path / "history.json")
    config = HistoryConfig(enabled=True, history_file=history_file, max_entries=3)
    store = HistoryStore(config)

    for _ in range(5):
        store.record("my-job", _make_result())

    raw = json.loads(Path(history_file).read_text())
    assert len(raw) == 3


def test_load_returns_entries(tmp_path):
    history_file = str(tmp_path / "history.json")
    config = HistoryConfig(enabled=True, history_file=history_file)
    store = HistoryStore(config)

    store.record("job-a", _make_result(success=True))
    store.record("job-b", _make_result(success=False, exit_code=1))

    entries = store.load()
    assert len(entries) == 2
    assert entries[0].job_name == "job-a"
    assert entries[1].success is False


def test_load_returns_empty_when_no_file(tmp_path):
    config = HistoryConfig(enabled=True, history_file=str(tmp_path / "missing.json"))
    store = HistoryStore(config)
    assert store.load() == []
