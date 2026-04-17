"""Tests for cronwrap.lockfile."""
import pytest
from pathlib import Path

from cronwrap.lockfile import LockConfig, LockFile, LockAcquireError


# --- LockConfig ---

def test_lock_config_disabled_by_default():
    cfg = LockConfig.from_env({})
    assert cfg.enabled is False


def test_lock_config_from_env():
    env = {
        "CRONWRAP_LOCK": "true",
        "CRONWRAP_LOCK_DIR": "/var/run",
        "CRONWRAP_JOB_NAME": "myjob",
        "CRONWRAP_LOCK_TIMEOUT": "5",
    }
    cfg = LockConfig.from_env(env)
    assert cfg.enabled is True
    assert cfg.lock_dir == "/var/run"
    assert cfg.job_name == "myjob"
    assert cfg.timeout == 5


def test_lock_path_construction():
    cfg = LockConfig(enabled=True, lock_dir="/tmp", job_name="backup")
    assert cfg.lock_path == Path("/tmp/backup.lock")


# --- LockFile disabled ---

def test_acquire_returns_true_when_disabled():
    cfg = LockConfig(enabled=False)
    lf = LockFile(cfg)
    assert lf.acquire() is True


def test_release_noop_when_disabled():
    cfg = LockConfig(enabled=False)
    lf = LockFile(cfg)
    lf.release()  # should not raise


# --- LockFile enabled ---

def test_acquire_and_release(tmp_path):
    cfg = LockConfig(enabled=True, lock_dir=str(tmp_path), job_name="test")
    lf = LockFile(cfg)
    assert lf.acquire() is True
    assert cfg.lock_path.exists()
    lf.release()
    assert not cfg.lock_path.exists()


def test_second_acquire_fails_immediately(tmp_path):
    cfg = LockConfig(enabled=True, lock_dir=str(tmp_path), job_name="test", timeout=0)
    lf1 = LockFile(cfg)
    lf2 = LockFile(cfg)
    assert lf1.acquire() is True
    assert lf2.acquire() is False
    lf1.release()


def test_context_manager_acquires_and_releases(tmp_path):
    cfg = LockConfig(enabled=True, lock_dir=str(tmp_path), job_name="ctx")
    with LockFile(cfg):
        assert cfg.lock_path.exists()
    assert not cfg.lock_path.exists()


def test_context_manager_raises_on_conflict(tmp_path):
    cfg = LockConfig(enabled=True, lock_dir=str(tmp_path), job_name="conflict", timeout=0)
    lf1 = LockFile(cfg)
    lf1.acquire()
    with pytest.raises(LockAcquireError):
        with LockFile(cfg):
            pass
    lf1.release()
