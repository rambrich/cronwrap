"""Tests for cronwrap.webhook_cli."""
import pytest
from unittest.mock import patch, MagicMock
from cronwrap.webhook import WebhookConfig
from cronwrap.webhook_cli import build_parser, cmd_status, cmd_test


def test_build_parser_has_subcommands():
    parser = build_parser()
    assert parser is not None


def test_cmd_status_output(capsys):
    cfg = WebhookConfig(enabled=True, url="http://example.com", on_failure=True, on_success=False, timeout=5)
    cmd_status(cfg)
    out = capsys.readouterr().out
    assert "http://example.com" in out
    assert "on_failure" in out


def test_cmd_status_no_url(capsys):
    cfg = WebhookConfig(enabled=False)
    cmd_status(cfg)
    out = capsys.readouterr().out
    assert "(not set)" in out


def test_cmd_test_exits_when_no_url():
    cfg = WebhookConfig(enabled=False)
    with pytest.raises(SystemExit):
        cmd_test(cfg, url=None, success=False)


def test_cmd_test_sends_payload(capsys):
    cfg = WebhookConfig(enabled=True, url="http://example.com/hook")
    mock_resp = MagicMock()
    mock_resp.status = 201
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        cmd_test(cfg, url=None, success=True)
    out = capsys.readouterr().out
    assert "201" in out


def test_cmd_test_url_override(capsys):
    cfg = WebhookConfig(enabled=False)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        cmd_test(cfg, url="http://override.com/hook", success=False)
    out = capsys.readouterr().out
    assert "200" in out
