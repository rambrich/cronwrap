"""Tests for cronwrap.cooldown."""
import json
import time
from pathlib import Path

import pytest

from cronwrap.cooldown import CooldownConfig, CooldownManager


@pytest.fixture
def tmp_config(tmp_path):
    return CooldownConfig(enabled=True, min_gap_seconds=60, state_dir=str(tmp_path))


def test_cooldown_config_disabled_by_default():
    cfg = CooldownConfig()
    assert cfg.enabled is False


def test_cooldown_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_COOLDOWN_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_COOLDOWN_MIN_GAP_SECONDS", "120")
    cfg = CooldownConfig.from_env()
    assert cfg.enabled is True
    assert cfg.min_gap_seconds == 120


def test_not_in_cooldown_when_disabled(tmp_path):
    cfg = CooldownConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CooldownManager(cfg, "job1")
    assert mgr.in_cooldown() is False


def test_not_in_cooldown_when_no_state(tmp_config):
    mgr = CooldownManager(tmp_config, "job1")
    assert mgr.in_cooldown() is False


def test_in_cooldown_after_recent_run(tmp_config):
    mgr = CooldownManager(tmp_config, "job1")
    mgr.record(time.time())
    assert mgr.in_cooldown() is True


def test_not_in_cooldown_after_gap_elapsed(tmp_config):
    mgr = CooldownManager(tmp_config, "job1")
    mgr.record(time.time() - 120)  # 120s ago, gap is 60s
    assert mgr.in_cooldown() is False


def test_seconds_remaining_positive_during_cooldown(tmp_config):
    mgr = CooldownManager(tmp_config, "job1")
    mgr.record(time.time())
    remaining = mgr.seconds_remaining()
    assert 0 < remaining <= 60


def test_seconds_remaining_zero_when_disabled(tmp_path):
    cfg = CooldownConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CooldownManager(cfg, "job1")
    assert mgr.seconds_remaining() == 0.0


def test_reset_clears_state(tmp_config):
    mgr = CooldownManager(tmp_config, "job1")
    mgr.record(time.time())
    assert mgr.in_cooldown() is True
    mgr.reset()
    assert mgr.in_cooldown() is False


def test_record_noop_when_disabled(tmp_path):
    cfg = CooldownConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CooldownManager(cfg, "job1")
    mgr.record(time.time())
    assert not (Path(tmp_path) / "job1.json").exists()
