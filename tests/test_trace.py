"""Tests for cronwrap.trace"""
import pytest
from unittest.mock import MagicMock
from cronwrap.trace import TraceConfig, TraceManager, TraceEntry
from cronwrap.runner import RunResult


def _result(success=True, exit_code=0, duration=1.2):
    return RunResult(
        exit_code=exit_code,
        stdout="out",
        stderr="",
        duration=duration,
        success=success,
        timed_out=False,
    )


def test_trace_config_disabled_by_default():
    cfg = TraceConfig()
    assert cfg.enabled is False


def test_trace_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_TRACE_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_TRACE_DIR", "/tmp/test_traces")
    cfg = TraceConfig.from_env()
    assert cfg.enabled is True
    assert cfg.trace_dir == "/tmp/test_traces"


def test_record_returns_none_when_disabled():
    mgr = TraceManager(TraceConfig(enabled=False))
    result = mgr.record(_result(), command="echo hi")
    assert result is None


def test_record_writes_entry(tmp_path):
    cfg = TraceConfig(enabled=True, trace_dir=str(tmp_path))
    mgr = TraceManager(cfg)
    entry = mgr.record(_result(), command="echo hi", tags={"env": "prod"})
    assert isinstance(entry, TraceEntry)
    assert entry.command == "echo hi"
    assert entry.success is True
    assert entry.tags == {"env": "prod"}
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1


def test_load_returns_none_for_missing(tmp_path):
    cfg = TraceConfig(enabled=True, trace_dir=str(tmp_path))
    mgr = TraceManager(cfg)
    assert mgr.load("nonexistent-id") is None


def test_load_returns_entry(tmp_path):
    cfg = TraceConfig(enabled=True, trace_dir=str(tmp_path))
    mgr = TraceManager(cfg)
    entry = mgr.record(_result(success=False, exit_code=1), command="false")
    loaded = mgr.load(entry.trace_id)
    assert loaded is not None
    assert loaded["exit_code"] == 1
    assert loaded["success"] is False


def test_list_traces_empty(tmp_path):
    cfg = TraceConfig(enabled=True, trace_dir=str(tmp_path))
    mgr = TraceManager(cfg)
    assert mgr.list_traces() == []


def test_list_traces_returns_all(tmp_path):
    cfg = TraceConfig(enabled=True, trace_dir=str(tmp_path))
    mgr = TraceManager(cfg)
    mgr.record(_result(), command="cmd1")
    mgr.record(_result(), command="cmd2")
    traces = mgr.list_traces()
    assert len(traces) == 2
    commands = {t["command"] for t in traces}
    assert commands == {"cmd1", "cmd2"}
