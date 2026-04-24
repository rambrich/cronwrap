"""Tests for cronwrap.pattern module."""
import pytest
from unittest.mock import patch

from cronwrap.pattern import PatternConfig, PatternMatch, PatternMatcher, PatternResult
from cronwrap.runner import RunResult


def _result(stdout: str = "", stderr: str = "") -> RunResult:
    return RunResult(command="echo test", returncode=0, stdout=stdout, stderr=stderr, duration=0.1)


def test_pattern_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        cfg = PatternConfig.from_env()
    assert cfg.enabled is False
    assert cfg.warn_patterns == []
    assert cfg.fail_patterns == []


def test_pattern_config_from_env():
    env = {
        "CRONWRAP_PATTERN_ENABLED": "true",
        "CRONWRAP_PATTERN_WARN": "WARNING,DEPRECATED",
        "CRONWRAP_PATTERN_FAIL": "ERROR,CRITICAL",
    }
    with patch.dict("os.environ", env, clear=True):
        cfg = PatternConfig.from_env()
    assert cfg.enabled is True
    assert cfg.warn_patterns == ["WARNING", "DEPRECATED"]
    assert cfg.fail_patterns == ["ERROR", "CRITICAL"]


def test_check_returns_none_when_disabled():
    cfg = PatternConfig(enabled=False, warn_patterns=["WARN"], fail_patterns=["ERROR"])
    matcher = PatternMatcher(cfg)
    assert matcher.check(_result(stdout="ERROR: something bad")) is None


def test_check_returns_empty_when_no_match():
    cfg = PatternConfig(enabled=True, warn_patterns=["WARN"], fail_patterns=["ERROR"])
    matcher = PatternMatcher(cfg)
    result = matcher.check(_result(stdout="everything is fine"))
    assert result is not None
    assert result.matches == []
    assert result.has_failures is False
    assert result.has_warnings is False


def test_check_detects_fail_pattern():
    cfg = PatternConfig(enabled=True, fail_patterns=["ERROR"])
    matcher = PatternMatcher(cfg)
    result = matcher.check(_result(stdout="line1\nERROR: disk full\nline3"))
    assert result is not None
    assert result.has_failures is True
    assert any(m.pattern == "ERROR" for m in result.matches)


def test_check_detects_warn_pattern_in_stderr():
    cfg = PatternConfig(enabled=True, warn_patterns=["DEPRECATED"])
    matcher = PatternMatcher(cfg)
    result = matcher.check(_result(stderr="DEPRECATED: use new API"))
    assert result is not None
    assert result.has_warnings is True
    assert result.matches[0].level == "warn"
    assert result.matches[0].matched_line == "DEPRECATED: use new API"


def test_check_detects_multiple_matches():
    cfg = PatternConfig(enabled=True, warn_patterns=["WARN"], fail_patterns=["ERROR"])
    matcher = PatternMatcher(cfg)
    output = "WARN: low disk\nERROR: out of memory\nWARN: high cpu"
    result = matcher.check(_result(stdout=output))
    assert result is not None
    assert len(result.matches) == 3
    levels = [m.level for m in result.matches]
    assert levels.count("fail") == 1
    assert levels.count("warn") == 2


def test_pattern_match_to_dict():
    m = PatternMatch(level="fail", pattern="ERROR", matched_line="ERROR: bad thing")
    d = m.to_dict()
    assert d == {"level": "fail", "pattern": "ERROR", "matched_line": "ERROR: bad thing"}


def test_check_uses_regex():
    cfg = PatternConfig(enabled=True, fail_patterns=[r"exit\s+code\s+\d+"])
    matcher = PatternMatcher(cfg)
    result = matcher.check(_result(stdout="process finished with exit code 1"))
    assert result is not None
    assert result.has_failures is True
