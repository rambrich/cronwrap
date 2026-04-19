"""Tests for cronwrap.drain."""
import json
import time
from unittest.mock import patch

import pytest

from cronwrap.drain import DrainConfig, DrainManager


@pytest.fixture
def tmp_config(tmp_path):
    return DrainConfig(enabled=True, state_dir=str(tmp_path), timeout_seconds=5)


def test_drain_config_disabled_by_default():
    config = DrainConfig()
    assert config.enabled is False


def test_drain_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DRAIN_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_DRAIN_TIMEOUT", "60")
    config = DrainConfig.from_env()
    assert config.enabled is True
    assert config.timeout_seconds == 60


def test_drain_config_invalid_timeout(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DRAIN_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_DRAIN_TIMEOUT", "notanint")
    config = DrainConfig.from_env()
    assert config.timeout_seconds == 300


def test_is_draining_false_when_disabled(tmp_path):
    config = DrainConfig(enabled=False, state_dir=str(tmp_path))
    mgr = DrainManager(config, "myjob")
    assert mgr.is_draining() is False


def test_is_draining_false_when_no_state(tmp_config):
    mgr = DrainManager(tmp_config, "myjob")
    assert mgr.is_draining() is False


def test_set_and_check_draining(tmp_config):
    mgr = DrainManager(tmp_config, "myjob")
    mgr.set_draining(True)
    assert mgr.is_draining() is True


def test_set_draining_false(tmp_config):
    mgr = DrainManager(tmp_config, "myjob")
    mgr.set_draining(True)
    mgr.set_draining(False)
    assert mgr.is_draining() is False


def test_reset_removes_state(tmp_config):
    mgr = DrainManager(tmp_config, "myjob")
    mgr.set_draining(True)
    mgr.reset()
    assert mgr.is_draining() is False


def test_wait_until_clear_returns_true_when_not_draining(tmp_config):
    mgr = DrainManager(tmp_config, "myjob")
    result = mgr.wait_until_clear(poll_interval=0.01)
    assert result is True


def test_wait_until_clear_returns_false_on_timeout(tmp_config):
    tmp_config.timeout_seconds = 0
    mgr = DrainManager(tmp_config, "myjob")
    mgr.set_draining(True)
    result = mgr.wait_until_clear(poll_interval=0.01)
    assert result is False


def test_set_draining_noop_when_disabled(tmp_path):
    config = DrainConfig(enabled=False, state_dir=str(tmp_path))
    mgr = DrainManager(config, "myjob")
    mgr.set_draining(True)  # should not raise or write
    assert not (tmp_path / "myjob.drain.json").exists()
