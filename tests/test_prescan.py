"""Tests for cronwrap.prescan module."""
import pytest
from unittest.mock import patch

from cronwrap.prescan import PrescanConfig, PrescanManager, PrescanResult
from cronwrap.runner import RunResult


def _result(stdout: str = "", stderr: str = "", returncode: int = 0) -> RunResult:
    return RunResult(
        command="echo test",
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration=0.1,
    )


def test_prescan_config_disabled_by_default():
    config = PrescanConfig()
    assert config.enabled is False
    assert config.warn_patterns == []
    assert config.fail_patterns == []


def test_prescan_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_PRESCAN_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_PRESCAN_WARN_PATTERNS", "WARNING,WARN")
    monkeypatch.setenv("CRONWRAP_PRESCAN_FAIL_PATTERNS", "ERROR,CRITICAL")
    config = PrescanConfig.from_env()
    assert config.enabled is True
    assert "WARNING" in config.warn_patterns
    assert "ERROR" in config.fail_patterns


def test_scan_returns_none_when_disabled():
    config = PrescanConfig(enabled=False)
    manager = PrescanManager(config)
    result = manager.scan(_result(stdout="ERROR: something bad"))
    assert result is None


def test_scan_detects_warn_pattern():
    config = PrescanConfig(enabled=True, warn_patterns=["WARNING"], fail_patterns=[])
    manager = PrescanManager(config)
    result = manager.scan(_result(stdout="WARNING: disk space low"))
    assert result is not None
    assert result.has_warnings is True
    assert result.has_failures is False
    assert "WARNING" in result.matched_warn


def test_scan_detects_fail_pattern():
    config = PrescanConfig(enabled=True, warn_patterns=[], fail_patterns=["ERROR"])
    manager = PrescanManager(config)
    result = manager.scan(_result(stdout="ERROR: fatal crash"))
    assert result is not None
    assert result.has_failures is True
    assert "ERROR" in result.matched_fail


def test_scan_no_match_returns_empty_result():
    config = PrescanConfig(enabled=True, warn_patterns=["WARNING"], fail_patterns=["ERROR"])
    manager = PrescanManager(config)
    result = manager.scan(_result(stdout="everything is fine"))
    assert result is not None
    assert result.has_warnings is False
    assert result.has_failures is False


def test_scan_checks_stderr_too():
    config = PrescanConfig(enabled=True, warn_patterns=[], fail_patterns=["CRITICAL"])
    manager = PrescanManager(config)
    result = manager.scan(_result(stdout="", stderr="CRITICAL failure detected"))
    assert result is not None
    assert result.has_failures is True


def test_should_override_failure_false_when_no_prescan():
    manager = PrescanManager(PrescanConfig(enabled=False))
    assert manager.should_override_failure(None) is False


def test_should_override_failure_true_when_fail_pattern_matched():
    manager = PrescanManager(PrescanConfig(enabled=True, fail_patterns=["ERROR"]))
    prescan = PrescanResult(matched_fail=["ERROR"])
    assert manager.should_override_failure(prescan) is True
