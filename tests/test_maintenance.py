"""Tests for cronwrap.maintenance."""
from __future__ import annotations

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch

from cronwrap.maintenance import MaintenanceConfig, MaintenanceWindow, MaintenanceManager


@pytest.fixture
def tmp_config(tmp_path):
    return MaintenanceConfig(enabled=True, state_dir=str(tmp_path))


# --- Config ---

def test_maintenance_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        cfg = MaintenanceConfig.from_env()
    assert cfg.enabled is False


def test_maintenance_config_from_env():
    with patch.dict("os.environ", {"CRONWRAP_MAINTENANCE_ENABLED": "1"}):
        cfg = MaintenanceConfig.from_env()
    assert cfg.enabled is True


# --- MaintenanceWindow ---

def test_window_is_active_within_range():
    now = time.time()
    w = MaintenanceWindow(start=now - 10, end=now + 10)
    assert w.is_active(now) is True


def test_window_is_inactive_after_end():
    now = time.time()
    w = MaintenanceWindow(start=now - 100, end=now - 10)
    assert w.is_active(now) is False


def test_window_roundtrip():
    w = MaintenanceWindow(start=1000.0, end=2000.0, reason="deploy")
    w2 = MaintenanceWindow.from_dict(w.to_dict())
    assert w2.start == 1000.0
    assert w2.end == 2000.0
    assert w2.reason == "deploy"


# --- MaintenanceManager ---

def test_is_active_false_when_disabled(tmp_path):
    cfg = MaintenanceConfig(enabled=False, state_dir=str(tmp_path))
    mgr = MaintenanceManager(cfg)
    # Even if a window file exists, disabled means not active
    now = time.time()
    w = MaintenanceWindow(start=now - 5, end=now + 3600)
    (tmp_path / "maintenance.json").write_text(json.dumps(w.to_dict()))
    assert mgr.is_active() is False


def test_is_active_false_when_no_state(tmp_config):
    mgr = MaintenanceManager(tmp_config)
    assert mgr.is_active() is False


def test_set_window_creates_file(tmp_config, tmp_path):
    mgr = MaintenanceManager(tmp_config)
    window = mgr.set_window(300, reason="testing")
    assert window.reason == "testing"
    assert (tmp_path / "maintenance.json").exists()


def test_is_active_true_after_set(tmp_config):
    mgr = MaintenanceManager(tmp_config)
    mgr.set_window(3600)
    assert mgr.is_active() is True


def test_clear_removes_window(tmp_config):
    mgr = MaintenanceManager(tmp_config)
    mgr.set_window(3600)
    mgr.clear()
    assert mgr.is_active() is False
    assert mgr.status() is None


def test_status_returns_none_when_no_file(tmp_config):
    mgr = MaintenanceManager(tmp_config)
    assert mgr.status() is None


def test_status_returns_window(tmp_config):
    mgr = MaintenanceManager(tmp_config)
    mgr.set_window(60, reason="patch")
    w = mgr.status()
    assert w is not None
    assert w.reason == "patch"
