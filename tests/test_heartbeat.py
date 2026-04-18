"""Tests for cronwrap.heartbeat."""
from unittest.mock import MagicMock, patch
import pytest

from cronwrap.heartbeat import HeartbeatConfig, HeartbeatManager
from cronwrap.runner import RunResult


def _result(success: bool, code: int = 0) -> RunResult:
    return RunResult(command="echo hi", returncode=code, stdout="", stderr="", duration=1.0, success=success)


def test_heartbeat_config_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CRONWRAP_HEARTBEAT_URL", raising=False)
    cfg = HeartbeatConfig.from_env()
    assert cfg.enabled is False


def test_heartbeat_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_HEARTBEAT_URL", "https://hc.example.com/abc")
    cfg = HeartbeatConfig.from_env()
    assert cfg.enabled is True
    assert cfg.url == "https://hc.example.com/abc"


def test_heartbeat_config_on_failure_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_HEARTBEAT_URL", "https://hc.example.com/abc")
    monkeypatch.setenv("CRONWRAP_HEARTBEAT_ON_FAILURE", "true")
    cfg = HeartbeatConfig.from_env()
    assert cfg.on_failure is True


def test_should_ping_false_when_disabled():
    cfg = HeartbeatConfig(enabled=False, url="https://example.com")
    mgr = HeartbeatManager(config=cfg)
    assert mgr.should_ping(_result(True)) is False


def test_should_ping_true_on_success():
    cfg = HeartbeatConfig(enabled=True, url="https://example.com", on_success=True)
    mgr = HeartbeatManager(config=cfg)
    assert mgr.should_ping(_result(True)) is True


def test_should_ping_false_on_failure_by_default():
    cfg = HeartbeatConfig(enabled=True, url="https://example.com", on_success=True, on_failure=False)
    mgr = HeartbeatManager(config=cfg)
    assert mgr.should_ping(_result(False)) is False


def test_ping_returns_none_when_disabled():
    cfg = HeartbeatConfig(enabled=False, url="https://example.com")
    mgr = HeartbeatManager(config=cfg)
    assert mgr.ping(_result(True)) is None


def test_ping_calls_url_on_success():
    cfg = HeartbeatConfig(enabled=True, url="https://hc.example.com/abc", on_success=True)
    mgr = HeartbeatManager(config=cfg)
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        status = mgr.ping(_result(True))
    mock_open.assert_called_once()
    assert status == 200


def test_ping_appends_fail_on_failure():
    cfg = HeartbeatConfig(enabled=True, url="https://hc.example.com/abc", on_failure=True)
    mgr = HeartbeatManager(config=cfg)
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        mgr.ping(_result(False, code=1))
    called_url = mock_open.call_args[0][0]
    assert called_url.endswith("/fail")
