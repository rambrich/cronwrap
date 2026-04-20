"""Tests for cronwrap.dedup."""
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.dedup import DedupConfig, DedupManager, _fingerprint


@pytest.fixture
def tmp_config(tmp_path):
    return DedupConfig(enabled=True, window_seconds=60, state_dir=str(tmp_path))


def test_dedup_config_disabled_by_default():
    cfg = DedupConfig()
    assert cfg.enabled is False


def test_dedup_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_DEDUP_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_DEDUP_WINDOW", "120")
    cfg = DedupConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 120


def test_fingerprint_deterministic():
    fp1 = _fingerprint("echo hello", {"env": "prod"})
    fp2 = _fingerprint("echo hello", {"env": "prod"})
    assert fp1 == fp2


def test_fingerprint_differs_by_command():
    assert _fingerprint("echo a") != _fingerprint("echo b")


def test_is_duplicate_false_when_disabled(tmp_config):
    tmp_config.enabled = False
    mgr = DedupManager(config=tmp_config)
    mgr.record("echo hi")
    assert mgr.is_duplicate("echo hi") is False


def test_is_duplicate_false_when_no_state(tmp_config):
    mgr = DedupManager(config=tmp_config)
    assert mgr.is_duplicate("echo hi") is False


def test_record_then_is_duplicate(tmp_config):
    mgr = DedupManager(config=tmp_config)
    mgr.record("echo hi")
    assert mgr.is_duplicate("echo hi") is True


def test_is_duplicate_false_after_window_expires(tmp_config, tmp_path):
    mgr = DedupManager(config=tmp_config)
    mgr.record("echo hi")
    # Manually backdate the state file
    from cronwrap.dedup import _fingerprint
    fp = _fingerprint("echo hi")
    state_file = tmp_path / f"{fp}.json"
    data = json.loads(state_file.read_text())
    data["last_run"] = time.time() - 9999
    state_file.write_text(json.dumps(data))
    assert mgr.is_duplicate("echo hi") is False


def test_reset_removes_state(tmp_config):
    mgr = DedupManager(config=tmp_config)
    mgr.record("echo hi")
    assert mgr.is_duplicate("echo hi") is True
    removed = mgr.reset("echo hi")
    assert removed is True
    assert mgr.is_duplicate("echo hi") is False


def test_reset_returns_false_when_no_state(tmp_config):
    mgr = DedupManager(config=tmp_config)
    assert mgr.reset("nonexistent") is False
