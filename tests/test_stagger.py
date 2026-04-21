"""Tests for cronwrap.stagger."""
from unittest.mock import patch
import os
import pytest

from cronwrap.stagger import StaggerConfig, StaggerManager, _offset_seconds


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_stagger_config_disabled_by_default():
    cfg = StaggerConfig.from_env()
    assert cfg.enabled is False


def test_stagger_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_STAGGER_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_STAGGER_WINDOW", "120")
    monkeypatch.setenv("CRONWRAP_STAGGER_SEED", "myjob")
    cfg = StaggerConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 120
    assert cfg.seed == "myjob"


def test_stagger_config_invalid_window_defaults_to_60(monkeypatch):
    monkeypatch.setenv("CRONWRAP_STAGGER_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_STAGGER_WINDOW", "notanumber")
    cfg = StaggerConfig.from_env()
    assert cfg.window_seconds == 60


def test_stagger_config_negative_window_clamped(monkeypatch):
    monkeypatch.setenv("CRONWRAP_STAGGER_WINDOW", "-10")
    cfg = StaggerConfig.from_env()
    assert cfg.window_seconds == 0


# ---------------------------------------------------------------------------
# _offset_seconds tests
# ---------------------------------------------------------------------------

def test_offset_seconds_deterministic_with_seed():
    a = _offset_seconds(60, "job-a")
    b = _offset_seconds(60, "job-a")
    assert a == b


def test_offset_seconds_within_window():
    for seed in ("alpha", "beta", "gamma", None):
        with patch("cronwrap.stagger.random") if seed is None else __import__("contextlib").nullcontext():
            val = _offset_seconds(30, seed if seed else "fixed-seed")
            assert 0.0 <= val < 30


def test_offset_seconds_different_seeds_differ():
    a = _offset_seconds(3600, "job-a")
    b = _offset_seconds(3600, "job-b")
    assert a != b


# ---------------------------------------------------------------------------
# StaggerManager tests
# ---------------------------------------------------------------------------

def test_delay_returns_zero_when_disabled():
    cfg = StaggerConfig(enabled=False, window_seconds=60, seed="x")
    mgr = StaggerManager(cfg)
    assert mgr.delay_seconds() == 0.0


def test_delay_returns_zero_when_window_zero():
    cfg = StaggerConfig(enabled=True, window_seconds=0, seed="x")
    mgr = StaggerManager(cfg)
    assert mgr.delay_seconds() == 0.0


def test_delay_returns_positive_when_enabled():
    cfg = StaggerConfig(enabled=True, window_seconds=60, seed="deterministic-seed")
    mgr = StaggerManager(cfg)
    assert mgr.delay_seconds() > 0.0


def test_apply_calls_sleep_and_returns_delay():
    cfg = StaggerConfig(enabled=True, window_seconds=60, seed="test-seed")
    mgr = StaggerManager(cfg)
    expected = mgr.delay_seconds()
    with patch("cronwrap.stagger.time.sleep") as mock_sleep:
        result = mgr.apply()
    mock_sleep.assert_called_once_with(expected)
    assert result == expected


def test_apply_skips_sleep_when_disabled():
    cfg = StaggerConfig(enabled=False, window_seconds=60, seed="x")
    mgr = StaggerManager(cfg)
    with patch("cronwrap.stagger.time.sleep") as mock_sleep:
        result = mgr.apply()
    mock_sleep.assert_not_called()
    assert result == 0.0
