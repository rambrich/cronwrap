"""Tests for cronwrap.timeout module."""
import pytest
from unittest.mock import patch
from cronwrap.timeout import TimeoutConfig, TimeoutExceededError, TimeoutManager


def test_timeout_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        cfg = TimeoutConfig.from_env()
    assert cfg.enabled is False


def test_timeout_config_from_env():
    with patch.dict("os.environ", {"CRONWRAP_TIMEOUT": "30"}):
        cfg = TimeoutConfig.from_env()
    assert cfg.enabled is True
    assert cfg.seconds == 30


def test_timeout_config_kill_after_default():
    with patch.dict("os.environ", {"CRONWRAP_TIMEOUT": "60"}):
        cfg = TimeoutConfig.from_env()
    assert cfg.kill_after == 5


def test_timeout_config_kill_after_custom():
    with patch.dict("os.environ", {"CRONWRAP_TIMEOUT": "60", "CRONWRAP_TIMEOUT_KILL_AFTER": "10"}):
        cfg = TimeoutConfig.from_env()
    assert cfg.kill_after == 10


def test_timeout_config_invalid_value():
    with patch.dict("os.environ", {"CRONWRAP_TIMEOUT": "abc"}):
        cfg = TimeoutConfig.from_env()
    assert cfg.enabled is False


def test_get_timeout_returns_none_when_disabled():
    mgr = TimeoutManager(TimeoutConfig(enabled=False))
    assert mgr.get_timeout() is None


def test_get_timeout_returns_seconds_when_enabled():
    mgr = TimeoutManager(TimeoutConfig(enabled=True, seconds=45))
    assert mgr.get_timeout() == 45


def test_check_result_no_raise_when_disabled():
    mgr = TimeoutManager(TimeoutConfig(enabled=False, seconds=10))
    mgr.check_result(0, 15.0)  # should not raise


def test_check_result_raises_when_elapsed_exceeds_timeout():
    mgr = TimeoutManager(TimeoutConfig(enabled=True, seconds=10))
    with pytest.raises(TimeoutExceededError) as exc_info:
        mgr.check_result(-9, 10.5)
    assert exc_info.value.seconds == 10


def test_check_result_no_raise_within_timeout():
    mgr = TimeoutManager(TimeoutConfig(enabled=True, seconds=30))
    mgr.check_result(0, 5.0)  # should not raise
