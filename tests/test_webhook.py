"""Tests for cronwrap.webhook."""
import pytest
from unittest.mock import patch, MagicMock
from cronwrap.webhook import WebhookConfig, WebhookManager, WebhookPayload
from cronwrap.runner import RunResult


def _result(success=True, exit_code=0, duration=1.0):
    return RunResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="hi",
        stderr="",
        success=success,
        duration=duration,
    )


def test_webhook_config_disabled_by_default():
    cfg = WebhookConfig()
    assert cfg.enabled is False


def test_webhook_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_WEBHOOK_URL", "http://example.com/hook")
    cfg = WebhookConfig.from_env()
    assert cfg.enabled is True
    assert cfg.url == "http://example.com/hook"


def test_webhook_config_on_success_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_WEBHOOK_URL", "http://example.com/hook")
    monkeypatch.setenv("CRONWRAP_WEBHOOK_ON_SUCCESS", "true")
    cfg = WebhookConfig.from_env()
    assert cfg.on_success is True


def test_should_send_false_when_disabled():
    cfg = WebhookConfig(enabled=False)
    mgr = WebhookManager(cfg)
    assert mgr.should_send(_result(success=False)) is False


def test_should_send_true_on_failure():
    cfg = WebhookConfig(enabled=True, url="http://x.com", on_failure=True)
    mgr = WebhookManager(cfg)
    assert mgr.should_send(_result(success=False, exit_code=1)) is True


def test_should_send_false_on_success_when_not_configured():
    cfg = WebhookConfig(enabled=True, url="http://x.com", on_success=False)
    mgr = WebhookManager(cfg)
    assert mgr.should_send(_result(success=True)) is False


def test_should_send_true_on_success_when_configured():
    cfg = WebhookConfig(enabled=True, url="http://x.com", on_success=True)
    mgr = WebhookManager(cfg)
    assert mgr.should_send(_result(success=True)) is True


def test_send_returns_none_when_disabled():
    cfg = WebhookConfig(enabled=False)
    mgr = WebhookManager(cfg)
    assert mgr.send(_result(success=False)) is None


def test_send_posts_and_returns_status():
    cfg = WebhookConfig(enabled=True, url="http://example.com/hook", on_failure=True)
    mgr = WebhookManager(cfg)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        status = mgr.send(_result(success=False, exit_code=1))
    assert status == 200


def test_send_returns_none_on_url_error():
    import urllib.error
    cfg = WebhookConfig(enabled=True, url="http://bad.invalid/hook", on_failure=True)
    mgr = WebhookManager(cfg)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
        status = mgr.send(_result(success=False, exit_code=1))
    assert status is None
