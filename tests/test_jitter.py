"""Tests for cronwrap.jitter."""
import pytest
from unittest.mock import patch

from cronwrap.jitter import JitterConfig, JitterManager


def test_jitter_config_disabled_by_default():
    config = JitterConfig()
    assert config.enabled is False
    assert config.max_seconds == 0


def test_jitter_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_JITTER_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_JITTER_MAX_SECONDS", "30")
    config = JitterConfig.from_env()
    assert config.enabled is True
    assert config.max_seconds == 30


def test_jitter_config_invalid_max_seconds(monkeypatch):
    monkeypatch.setenv("CRONWRAP_JITTER_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_JITTER_MAX_SECONDS", "bad")
    config = JitterConfig.from_env()
    assert config.max_seconds == 0


def test_delay_returns_zero_when_disabled():
    mgr = JitterManager(JitterConfig(enabled=False, max_seconds=10))
    assert mgr.delay_seconds() == 0.0


def test_delay_returns_zero_when_max_is_zero():
    mgr = JitterManager(JitterConfig(enabled=True, max_seconds=0))
    assert mgr.delay_seconds() == 0.0


def test_delay_within_range():
    mgr = JitterManager(JitterConfig(enabled=True, max_seconds=60, seed=42))
    for _ in range(20):
        d = mgr.delay_seconds()
        assert 0.0 <= d <= 60.0


def test_apply_calls_sleep_with_delay():
    mgr = JitterManager(JitterConfig(enabled=True, max_seconds=10, seed=1))
    slept = []
    delay = mgr.apply(sleep_fn=slept.append)
    assert len(slept) == 1
    assert slept[0] == delay
    assert 0.0 <= delay <= 10.0


def test_apply_does_not_sleep_when_disabled():
    mgr = JitterManager(JitterConfig(enabled=False, max_seconds=10))
    slept = []
    delay = mgr.apply(sleep_fn=slept.append)
    assert delay == 0.0
    assert slept == []


def test_seed_produces_deterministic_delays():
    mgr1 = JitterManager(JitterConfig(enabled=True, max_seconds=100, seed=99))
    mgr2 = JitterManager(JitterConfig(enabled=True, max_seconds=100, seed=99))
    delays1 = [mgr1.delay_seconds() for _ in range(5)]
    delays2 = [mgr2.delay_seconds() for _ in range(5)]
    assert delays1 == delays2
