"""Tests for cronwrap.alerts module."""
import pytest
from unittest.mock import patch, MagicMock

from cronwrap.runner import RunResult
from cronwrap.alerts import AlertRule, AlertConfig, AlertManager


def _make_result(returncode=0, duration=1.0, stdout="ok", stderr=""):
    return RunResult(returncode=returncode, stdout=stdout, stderr=stderr, duration=duration)


def test_alert_rule_matches_failure():
    rule = AlertRule(alert_on_failure=True)
    assert rule.matches(_make_result(returncode=1)) is True
    assert rule.matches(_make_result(returncode=0)) is False


def test_alert_rule_matches_success():
    rule = AlertRule(alert_on_failure=False, alert_on_success=True)
    assert rule.matches(_make_result(returncode=0)) is True
    assert rule.matches(_make_result(returncode=1)) is False


def test_alert_rule_matches_duration():
    rule = AlertRule(alert_on_failure=False, max_duration_seconds=5.0)
    assert rule.matches(_make_result(duration=6.0)) is True
    assert rule.matches(_make_result(duration=4.0)) is False


def test_alert_config_disabled_by_default():
    config = AlertConfig.from_env()
    assert config.enabled is False


def test_alert_config_from_env():
    env = {
        "CRONWRAP_ALERTS_ENABLED": "true",
        "CRONWRAP_ALERT_WEBHOOK_URL": "http://example.com/hook",
        "CRONWRAP_ALERT_MAX_DURATION": "30",
    }
    with patch.dict("os.environ", env):
        config = AlertConfig.from_env()
    assert config.enabled is True
    assert config.webhook_url == "http://example.com/hook"
    assert config.rules[0].max_duration_seconds == 30.0


def test_should_alert_false_when_disabled():
    config = AlertConfig(enabled=False, rules=[AlertRule(alert_on_failure=True)])
    mgr = AlertManager(config)
    assert mgr.should_alert(_make_result(returncode=1)) is False


def test_should_alert_true_on_failure():
    config = AlertConfig(enabled=True, rules=[AlertRule(alert_on_failure=True)])
    mgr = AlertManager(config)
    assert mgr.should_alert(_make_result(returncode=1)) is True


def test_build_payload_keys():
    config = AlertConfig(enabled=True, rules=[])
    mgr = AlertManager(config)
    payload = mgr.build_payload(_make_result(), job_name="backup")
    assert payload["job"] == "backup"
    assert "returncode" in payload
    assert "duration" in payload


def test_send_returns_false_no_webhook():
    config = AlertConfig(enabled=True, rules=[AlertRule(alert_on_failure=True)], webhook_url=None)
    mgr = AlertManager(config)
    assert mgr.send(_make_result(returncode=1)) is False


def test_send_posts_to_webhook():
    config = AlertConfig(
        enabled=True,
        rules=[AlertRule(alert_on_failure=True)],
        webhook_url="http://example.com/hook",
    )
    mgr = AlertManager(config)
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_ctx):
        result = mgr.send(_make_result(returncode=1), job_name="test")
    assert result is True
