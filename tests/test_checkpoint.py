"""Tests for cronwrap.checkpoint."""
import json
import pytest
from unittest.mock import patch
from cronwrap.checkpoint import CheckpointConfig, CheckpointEntry, CheckpointManager


@pytest.fixture
def tmp_config(tmp_path):
    return CheckpointConfig(enabled=True, state_dir=str(tmp_path))


def test_checkpoint_config_disabled_by_default():
    cfg = CheckpointConfig()
    assert cfg.enabled is False


def test_checkpoint_config_from_env():
    with patch.dict("os.environ", {"CRONWRAP_CHECKPOINT_ENABLED": "true", "CRONWRAP_CHECKPOINT_DIR": "/tmp/cp"}):
        cfg = CheckpointConfig.from_env()
    assert cfg.enabled is True
    assert cfg.state_dir == "/tmp/cp"


def test_load_returns_none_when_disabled(tmp_path):
    cfg = CheckpointConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CheckpointManager(cfg)
    assert mgr.load("echo hi") is None


def test_load_returns_none_when_no_file(tmp_config):
    mgr = CheckpointManager(tmp_config)
    assert mgr.load("echo hi") is None


def test_save_and_load_roundtrip(tmp_config):
    mgr = CheckpointManager(tmp_config)
    entry = CheckpointEntry(command="echo hi", last_success_at=1000.0, last_failure_at=None)
    mgr.save(entry)
    loaded = mgr.load("echo hi")
    assert loaded is not None
    assert loaded.command == "echo hi"
    assert loaded.last_success_at == 1000.0


def test_update_success(tmp_config):
    mgr = CheckpointManager(tmp_config)
    entry = mgr.update("echo hi", success=True)
    assert entry is not None
    assert entry.last_success_at is not None
    assert entry.consecutive_failures == 0


def test_update_failure_increments_counter(tmp_config):
    mgr = CheckpointManager(tmp_config)
    mgr.update("echo hi", success=False)
    entry = mgr.update("echo hi", success=False)
    assert entry.consecutive_failures == 2


def test_update_success_resets_failures(tmp_config):
    mgr = CheckpointManager(tmp_config)
    mgr.update("echo hi", success=False)
    mgr.update("echo hi", success=False)
    entry = mgr.update("echo hi", success=True)
    assert entry.consecutive_failures == 0


def test_update_returns_none_when_disabled(tmp_path):
    cfg = CheckpointConfig(enabled=False, state_dir=str(tmp_path))
    mgr = CheckpointManager(cfg)
    assert mgr.update("echo hi", success=True) is None


def test_update_stores_metadata(tmp_config):
    mgr = CheckpointManager(tmp_config)
    entry = mgr.update("echo hi", success=True, metadata={"job": "nightly"})
    assert entry.metadata["job"] == "nightly"
    loaded = mgr.load("echo hi")
    assert loaded.metadata["job"] == "nightly"
