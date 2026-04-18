"""Tests for cronwrap.backoff."""
import os
import pytest
from unittest.mock import patch
from cronwrap.backoff import BackoffConfig, BackoffManager, compute_delay


def test_config_disabled_by_default():
    cfg = BackoffConfig.from_env()
    assert cfg.enabled is False


def test_config_from_env():
    env = {
        "CRONWRAP_BACKOFF_ENABLED": "true",
        "CRONWRAP_BACKOFF_BASE_DELAY": "2.0",
        "CRONWRAP_BACKOFF_MAX_DELAY": "30.0",
        "CRONWRAP_BACKOFF_MULTIPLIER": "3.0",
        "CRONWRAP_BACKOFF_JITTER": "false",
    }
    with patch.dict(os.environ, env):
        cfg = BackoffConfig.from_env()
    assert cfg.enabled is True
    assert cfg.base_delay == 2.0
    assert cfg.max_delay == 30.0
    assert cfg.multiplier == 3.0
    assert cfg.jitter is False


def test_compute_delay_disabled_returns_zero():
    cfg = BackoffConfig(enabled=False)
    assert compute_delay(cfg, 0) == 0.0
    assert compute_delay(cfg, 5) == 0.0


def test_compute_delay_no_jitter():
    cfg = BackoffConfig(enabled=True, base_delay=1.0, multiplier=2.0, max_delay=100.0, jitter=False)
    assert compute_delay(cfg, 0) == 1.0
    assert compute_delay(cfg, 1) == 2.0
    assert compute_delay(cfg, 2) == 4.0


def test_compute_delay_capped_at_max():
    cfg = BackoffConfig(enabled=True, base_delay=10.0, multiplier=10.0, max_delay=50.0, jitter=False)
    assert compute_delay(cfg, 3) == 50.0


def test_backoff_manager_calls_sleep():
    cfg = BackoffConfig(enabled=True, base_delay=5.0, multiplier=1.0, max_delay=10.0, jitter=False)
    slept = []
    mgr = BackoffManager(cfg, sleep_fn=slept.append)
    delay = mgr.wait(0)
    assert delay == 5.0
    assert slept == [5.0]


def test_backoff_manager_no_sleep_when_disabled():
    cfg = BackoffConfig(enabled=False)
    slept = []
    mgr = BackoffManager(cfg, sleep_fn=slept.append)
    delay = mgr.wait(0)
    assert delay == 0.0
    assert slept == []
