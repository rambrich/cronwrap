"""Tests for cronwrap.sampling."""
import pytest
from unittest.mock import patch

from cronwrap.sampling import SamplingConfig, SamplingManager


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_sampling_config_disabled_by_default():
    cfg = SamplingConfig()
    assert cfg.enabled is False
    assert cfg.rate == 1.0


def test_sampling_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SAMPLING_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_SAMPLING_RATE", "0.25")
    cfg = SamplingConfig.from_env()
    assert cfg.enabled is True
    assert cfg.rate == pytest.approx(0.25)


def test_sampling_config_clamps_rate(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SAMPLING_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_SAMPLING_RATE", "99.0")
    cfg = SamplingConfig.from_env()
    assert cfg.rate == pytest.approx(1.0)


def test_sampling_config_invalid_rate_defaults_to_one(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SAMPLING_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_SAMPLING_RATE", "not-a-number")
    cfg = SamplingConfig.from_env()
    assert cfg.rate == pytest.approx(1.0)


def test_sampling_config_seed_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SAMPLING_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_SAMPLING_SEED", "42")
    cfg = SamplingConfig.from_env()
    assert cfg.seed == 42


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

def test_should_run_true_when_disabled():
    mgr = SamplingManager(SamplingConfig(enabled=False, rate=0.0))
    assert mgr.should_run() is True


def test_should_run_true_when_rate_is_one():
    mgr = SamplingManager(SamplingConfig(enabled=True, rate=1.0))
    assert mgr.should_run() is True


def test_should_run_false_when_rate_is_zero():
    mgr = SamplingManager(SamplingConfig(enabled=True, rate=0.0))
    assert mgr.should_run() is False


def test_should_run_deterministic_with_seed():
    cfg = SamplingConfig(enabled=True, rate=0.5, seed=0)
    mgr1 = SamplingManager(cfg)
    mgr2 = SamplingManager(cfg)
    results1 = [mgr1.should_run() for _ in range(10)]
    results2 = [mgr2.should_run() for _ in range(10)]
    assert results1 == results2


def test_skipped_message_contains_rate():
    mgr = SamplingManager(SamplingConfig(enabled=True, rate=0.1))
    msg = mgr.skipped_message()
    assert "0.10" in msg
    assert "sampler" in msg
