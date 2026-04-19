"""Tests for cronwrap.snapshot."""
import pytest
from unittest.mock import patch
from cronwrap.snapshot import SnapshotConfig, SnapshotManager, SnapshotEntry
from cronwrap.runner import RunResult


def _result(stdout="hello", stderr="", exit_code=0, duration=1.0):
    return RunResult(command="echo hi", stdout=stdout, stderr=stderr,
                     exit_code=exit_code, duration=duration, attempts=1)


def test_snapshot_config_disabled_by_default():
    config = SnapshotConfig()
    assert config.enabled is False


def test_snapshot_config_from_env():
    with patch.dict("os.environ", {"CRONWRAP_SNAPSHOT_ENABLED": "true",
                                    "CRONWRAP_SNAPSHOT_DIR": "/tmp/snaps"}):
        config = SnapshotConfig.from_env()
    assert config.enabled is True
    assert config.state_dir == "/tmp/snaps"


def test_record_returns_none_when_disabled(tmp_path):
    config = SnapshotConfig(enabled=False, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    assert mgr.record("myjob", _result()) is None


def test_record_writes_entry(tmp_path):
    config = SnapshotConfig(enabled=True, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    entry = mgr.record("myjob", _result(stdout="output"))
    assert entry is not None
    assert entry.job_name == "myjob"
    assert len(entry.output_hash) == 64  # sha256 hex


def test_load_returns_none_when_no_file(tmp_path):
    config = SnapshotConfig(enabled=True, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    assert mgr.load("nonexistent") is None


def test_load_returns_entry_after_record(tmp_path):
    config = SnapshotConfig(enabled=True, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    mgr.record("myjob", _result(stdout="data"))
    loaded = mgr.load("myjob")
    assert loaded is not None
    assert loaded.job_name == "myjob"


def test_has_changed_true_when_no_previous(tmp_path):
    config = SnapshotConfig(enabled=True, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    assert mgr.has_changed("myjob", _result()) is True


def test_has_changed_false_when_same_output(tmp_path):
    config = SnapshotConfig(enabled=True, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    r = _result(stdout="same")
    mgr.record("myjob", r)
    assert mgr.has_changed("myjob", r) is False


def test_has_changed_true_when_output_differs(tmp_path):
    config = SnapshotConfig(enabled=True, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    mgr.record("myjob", _result(stdout="old"))
    assert mgr.has_changed("myjob", _result(stdout="new")) is True


def test_has_changed_false_when_disabled(tmp_path):
    config = SnapshotConfig(enabled=False, state_dir=str(tmp_path))
    mgr = SnapshotManager(config)
    assert mgr.has_changed("myjob", _result()) is False
