"""Tests for cronwrap.suppress."""
import time
import pytest
from unittest.mock import patch

from cronwrap.runner import RunResult
from cronwrap.suppress import SuppressConfig, SuppressManager, SuppressState


def _result(success: bool, command: str = "echo hello") -> RunResult:
    return RunResult(
        command=command,
        returncode=0 if success else 1,
        stdout="ok" if success else "",
        stderr="" if success else "error",
        duration=0.1,
        success=success,
        attempts=1,
    )


@pytest.fixture
def tmp_config(tmp_path):
    return SuppressConfig(
        enabled=True,
        window_seconds=3600,
        threshold=3,
        state_dir=str(tmp_path),
    )


def test_suppress_config_disabled_by_default():
    cfg = SuppressConfig()
    assert cfg.enabled is False


def test_suppress_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SUPPRESS_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_SUPPRESS_WINDOW", "1800")
    monkeypatch.setenv("CRONWRAP_SUPPRESS_THRESHOLD", "5")
    cfg = SuppressConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 1800
    assert cfg.threshold == 5


def test_should_suppress_false_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = SuppressManager(tmp_config)
    assert mgr.should_suppress(_result(False)) is False


def test_should_suppress_false_on_success(tmp_config):
    mgr = SuppressManager(tmp_config)
    assert mgr.should_suppress(_result(True)) is False


def test_should_suppress_false_below_threshold(tmp_config):
    mgr = SuppressManager(tmp_config)
    r = _result(False)
    assert mgr.should_suppress(r) is False  # count=1
    assert mgr.should_suppress(r) is False  # count=2


def test_should_suppress_true_at_threshold(tmp_config):
    mgr = SuppressManager(tmp_config)
    r = _result(False)
    mgr.should_suppress(r)  # count=1
    mgr.should_suppress(r)  # count=2
    assert mgr.should_suppress(r) is True  # count=3, threshold reached


def test_should_suppress_resets_after_window(tmp_config):
    mgr = SuppressManager(tmp_config)
    r = _result(False)
    mgr.should_suppress(r)
    mgr.should_suppress(r)
    # Simulate window expiry by patching time
    with patch("cronwrap.suppress.time.time", return_value=time.time() + 7200):
        result = mgr.should_suppress(r)
    # After window reset, count restarts at 1 — should not suppress
    assert result is False


def test_reset_removes_state(tmp_config):
    mgr = SuppressManager(tmp_config)
    r = _result(False)
    mgr.should_suppress(r)
    path = mgr._state_path(r.command)
    assert path.exists()
    mgr.reset(r.command)
    assert not path.exists()


def test_state_to_dict_and_from_dict():
    now = time.time()
    s = SuppressState(fingerprint="cmd", count=2, first_seen=now, last_seen=now, suppressed=False)
    d = s.to_dict()
    s2 = SuppressState.from_dict(d)
    assert s2.fingerprint == "cmd"
    assert s2.count == 2
    assert s2.suppressed is False
