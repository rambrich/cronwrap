"""Tests for cronwrap.circuit_breaker."""
import json
import time
import pytest
from unittest.mock import patch
from cronwrap.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitOpenError,
)


@pytest.fixture
def cfg(tmp_path):
    return CircuitBreakerConfig(enabled=True, threshold=3, window=3600, cooldown=600,
                                state_dir=str(tmp_path))


def test_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        c = CircuitBreakerConfig.from_env()
    assert c.enabled is False


def test_config_from_env(tmp_path):
    env = {"CRONWRAP_CIRCUIT_BREAKER": "true", "CRONWRAP_CIRCUIT_THRESHOLD": "5"}
    with patch.dict("os.environ", env):
        c = CircuitBreakerConfig.from_env()
    assert c.enabled is True
    assert c.threshold == 5


def test_check_passes_when_disabled(tmp_path):
    cfg = CircuitBreakerConfig(enabled=False, state_dir=str(tmp_path))
    cb = CircuitBreaker(cfg, "job")
    cb.check()  # should not raise


def test_check_passes_when_no_state(cfg):
    cb = CircuitBreaker(cfg, "job")
    cb.check()  # no state file — should pass


def test_circuit_opens_after_threshold(cfg):
    cb = CircuitBreaker(cfg, "job")
    for _ in range(3):
        cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.check()


def test_circuit_does_not_open_below_threshold(cfg):
    cb = CircuitBreaker(cfg, "job")
    cb.record_failure()
    cb.record_failure()
    cb.check()  # only 2 failures, threshold=3 — should pass


def test_record_success_resets_circuit(cfg):
    cb = CircuitBreaker(cfg, "job")
    for _ in range(3):
        cb.record_failure()
    cb.record_success()
    cb.check()  # should not raise after reset


def test_cooldown_expiry_resets_circuit(cfg):
    cb = CircuitBreaker(cfg, "job")
    for _ in range(3):
        cb.record_failure()
    # Simulate cooldown expired by backdating opened_at
    state_path = cb._path
    data = json.loads(state_path.read_text())
    data["opened_at"] = time.time() - 700  # beyond 600s cooldown
    state_path.write_text(json.dumps(data))
    cb.check()  # should not raise


def test_old_failures_outside_window_ignored(cfg):
    cb = CircuitBreaker(cfg, "job")
    old_time = time.time() - 7200  # 2 hours ago, beyond window
    state_path = cb._path
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"failures": [old_time, old_time, old_time], "opened_at": None}))
    cb.record_failure()  # only 1 recent failure
    cb.check()  # should not raise
