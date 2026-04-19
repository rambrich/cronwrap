"""Tests for cronwrap.runbook."""
import pytest
from unittest.mock import MagicMock
from cronwrap.runbook import RunbookConfig, RunbookEntry, RunbookManager
from cronwrap.runner import RunResult


def _result(success=True, command="echo hi", duration=1.0):
    return RunResult(command=command, returncode=0 if success else 1,
                     stdout="ok", stderr="", duration=duration, success=success)


def test_runbook_config_disabled_by_default():
    cfg = RunbookConfig()
    assert cfg.enabled is False


def test_runbook_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_RUNBOOK_URL", "https://wiki.example.com/runbook")
    monkeypatch.setenv("CRONWRAP_RUNBOOK_NOTES", "Check disk space first.")
    cfg = RunbookConfig.from_env()
    assert cfg.enabled is True
    assert cfg.url == "https://wiki.example.com/runbook"
    assert cfg.notes == "Check disk space first."


def test_runbook_config_no_url_means_disabled(monkeypatch):
    monkeypatch.delenv("CRONWRAP_RUNBOOK_URL", raising=False)
    cfg = RunbookConfig.from_env()
    assert cfg.enabled is False


def test_should_print_false_when_disabled():
    cfg = RunbookConfig(enabled=False, url="https://example.com")
    mgr = RunbookManager(cfg)
    assert mgr.should_print(_result(success=False)) is False


def test_should_print_true_on_failure_by_default():
    cfg = RunbookConfig(enabled=True, url="https://example.com", print_on_failure=True)
    mgr = RunbookManager(cfg)
    assert mgr.should_print(_result(success=False)) is True


def test_should_print_false_on_success_by_default():
    cfg = RunbookConfig(enabled=True, url="https://example.com", print_on_success=False)
    mgr = RunbookManager(cfg)
    assert mgr.should_print(_result(success=True)) is False


def test_should_print_true_on_success_when_configured():
    cfg = RunbookConfig(enabled=True, url="https://example.com", print_on_success=True)
    mgr = RunbookManager(cfg)
    assert mgr.should_print(_result(success=True)) is True


def test_build_entry_returns_none_when_disabled():
    cfg = RunbookConfig(enabled=False)
    mgr = RunbookManager(cfg)
    assert mgr.build_entry(_result(success=False)) is None


def test_build_entry_returns_entry_on_failure():
    cfg = RunbookConfig(enabled=True, url="https://wiki.example.com", notes="tip", print_on_failure=True)
    mgr = RunbookManager(cfg)
    entry = mgr.build_entry(_result(success=False, command="backup.sh"))
    assert entry is not None
    assert entry.url == "https://wiki.example.com"
    assert entry.notes == "tip"
    assert entry.command == "backup.sh"
    assert entry.success is False


def test_entry_render_contains_url_and_status():
    entry = RunbookEntry(url="https://example.com", notes="", command="job.sh", success=False)
    rendered = entry.render()
    assert "https://example.com" in rendered
    assert "FAILURE" in rendered


def test_print_runbook_returns_none_when_not_applicable():
    cfg = RunbookConfig(enabled=True, url="https://example.com", print_on_failure=True, print_on_success=False)
    mgr = RunbookManager(cfg)
    result = mgr.print_runbook(_result(success=True))
    assert result is None


def test_print_runbook_prints_and_returns_string(capsys):
    cfg = RunbookConfig(enabled=True, url="https://wiki.example.com", print_on_failure=True)
    mgr = RunbookManager(cfg)
    rendered = mgr.print_runbook(_result(success=False))
    assert rendered is not None
    captured = capsys.readouterr()
    assert "Runbook" in captured.out
