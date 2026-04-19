import json
import time
from pathlib import Path

import pytest

from cronwrap.deadletter import DeadLetterConfig, DeadLetterQueue, DeadLetterEntry
from cronwrap.runner import RunResult


def _result(success=False, exit_code=1, command="echo hi", duration=1.0):
    return RunResult(
        command=command,
        exit_code=exit_code,
        stdout="out",
        stderr="err",
        duration=duration,
        success=success,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return DeadLetterConfig(enabled=True, directory=str(tmp_path / "dl"), max_entries=5)


def test_config_disabled_by_default():
    cfg = DeadLetterConfig.from_env()
    assert not cfg.enabled


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DEADLETTER_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_DEADLETTER_DIR", "/tmp/dl_test")
    monkeypatch.setenv("CRONWRAP_DEADLETTER_MAX", "50")
    cfg = DeadLetterConfig.from_env()
    assert cfg.enabled
    assert cfg.directory == "/tmp/dl_test"
    assert cfg.max_entries == 50


def test_push_returns_none_when_disabled():
    cfg = DeadLetterConfig(enabled=False)
    q = DeadLetterQueue(cfg)
    assert q.push(_result(success=False)) is None


def test_push_returns_none_on_success(tmp_config):
    q = DeadLetterQueue(tmp_config)
    assert q.push(_result(success=True, exit_code=0)) is None


def test_push_writes_file(tmp_config):
    q = DeadLetterQueue(tmp_config)
    path = q.push(_result())
    assert path is not None
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["exit_code"] == 1
    assert data["command"] == "echo hi"


def test_list_entries(tmp_config):
    q = DeadLetterQueue(tmp_config)
    q.push(_result())
    q.push(_result(command="ls"))
    entries = q.list_entries()
    assert len(entries) == 2
    assert all(isinstance(e, DeadLetterEntry) for e in entries)


def test_clear_removes_all(tmp_config):
    q = DeadLetterQueue(tmp_config)
    q.push(_result())
    q.push(_result())
    removed = q.clear()
    assert removed == 2
    assert q.list_entries() == []


def test_eviction_respects_max(tmp_config):
    q = DeadLetterQueue(tmp_config)
    for i in range(7):
        time.sleep(0.01)
        q.push(_result(command=f"cmd{i}"))
    entries = q.list_entries()
    assert len(entries) <= tmp_config.max_entries
