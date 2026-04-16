"""Tests for cronwrap.notifier."""

import pytest
from unittest.mock import MagicMock, patch

from cronwrap.notifier import Notifier, NotifierConfig
from cronwrap.runner import RunResult


def _make_result(returncode=1, stdout="out", stderr="err", attempts=1, command="echo hi"):
    return RunResult(
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        attempts=attempts,
    )


def test_should_notify_false_when_no_recipients():
    config = NotifierConfig(to_addrs=[])
    notifier = Notifier(config)
    assert not notifier.should_notify()


def test_should_notify_true_when_recipients_set():
    config = NotifierConfig(to_addrs=["ops@example.com"])
    notifier = Notifier(config)
    assert notifier.should_notify()


def test_notify_failure_sends_email():
    config = NotifierConfig(to_addrs=["ops@example.com"], from_addr="cron@host")
    notifier = Notifier(config)
    result = _make_result(returncode=1)

    with patch("cronwrap.notifier.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        notifier.notify_failure(result, job_name="backup")
        mock_server.sendmail.assert_called_once()
        args = mock_server.sendmail.call_args[0]
        assert args[0] == "cron@host"
        assert "ops@example.com" in args[1]
        assert "FAILED" in args[2]
        assert "backup" in args[2]


def test_notify_success_sends_email():
    config = NotifierConfig(to_addrs=["ops@example.com"])
    notifier = Notifier(config)
    result = _make_result(returncode=0)

    with patch("cronwrap.notifier.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        notifier.notify_success(result, job_name="backup")
        mock_server.sendmail.assert_called_once()
        assert "OK" in mock_server.sendmail.call_args[0][2]


def test_notify_skipped_when_no_recipients():
    config = NotifierConfig(to_addrs=[])
    notifier = Notifier(config)
    result = _make_result(returncode=1)

    with patch("cronwrap.notifier.smtplib.SMTP") as mock_smtp_cls:
        notifier.notify_failure(result)
        mock_smtp_cls.assert_not_called()


def test_from_env_parses_recipients(monkeypatch):
    monkeypatch.setenv("CRONWRAP_ALERT_TO", "a@x.com, b@x.com")
    monkeypatch.setenv("CRONWRAP_SMTP_HOST", "mail.example.com")
    monkeypatch.setenv("CRONWRAP_SMTP_PORT", "587")
    monkeypatch.setenv("CRONWRAP_SMTP_TLS", "true")
    config = NotifierConfig.from_env()
    assert config.to_addrs == ["a@x.com", "b@x.com"]
    assert config.smtp_host == "mail.example.com"
    assert config.smtp_port == 587
    assert config.use_tls is True
