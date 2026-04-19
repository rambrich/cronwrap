"""Tests for cronwrap.dispatch."""
import pytest
from cronwrap.runner import RunResult
from cronwrap.dispatch import DispatchConfig, DispatchManager


def _result(exit_code: int = 0) -> RunResult:
    return RunResult(command="echo hi", exit_code=exit_code, stdout="hi", stderr="", duration=0.1, retries=0)


def test_config_enabled_by_default():
    cfg = DispatchConfig()
    assert cfg.enabled is True


def test_config_from_env_disabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DISPATCH_ENABLED", "false")
    cfg = DispatchConfig.from_env()
    assert cfg.enabled is False


def test_config_from_env_events(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DISPATCH_EVENTS", "success,complete")
    cfg = DispatchConfig.from_env()
    assert "success" in cfg.events
    assert "complete" in cfg.events


def test_on_registers_handler():
    mgr = DispatchManager(DispatchConfig())
    calls = []
    mgr.on("success", lambda r: calls.append(r))
    mgr.emit("success", _result(0))
    assert len(calls) == 1


def test_emit_returns_empty_when_disabled():
    cfg = DispatchConfig(enabled=False)
    mgr = DispatchManager(cfg)
    calls = []
    mgr.on("failure", lambda r: calls.append(r))
    fired = mgr.emit("failure", _result(1))
    assert fired == []
    assert calls == []


def test_emit_skips_event_not_in_config():
    cfg = DispatchConfig(enabled=True, events=["success"])
    mgr = DispatchManager(cfg)
    calls = []
    mgr.on("failure", lambda r: calls.append(r))
    fired = mgr.emit("failure", _result(1))
    assert fired == []


def test_emit_for_result_success():
    mgr = DispatchManager(DispatchConfig(enabled=True, events=["success", "failure", "complete"]))
    log = []
    mgr.on("success", lambda r: log.append("success"))
    mgr.on("failure", lambda r: log.append("failure"))
    mgr.on("complete", lambda r: log.append("complete"))
    mgr.emit_for_result(_result(0))
    assert "success" in log
    assert "failure" not in log
    assert "complete" in log


def test_emit_for_result_failure():
    mgr = DispatchManager(DispatchConfig(enabled=True, events=["success", "failure", "complete"]))
    log = []
    mgr.on("success", lambda r: log.append("success"))
    mgr.on("failure", lambda r: log.append("failure"))
    mgr.emit_for_result(_result(1))
    assert "failure" in log
    assert "success" not in log


def test_on_unknown_event_raises():
    mgr = DispatchManager(DispatchConfig())
    with pytest.raises(ValueError, match="Unknown event"):
        mgr.on("unknown", lambda r: None)
