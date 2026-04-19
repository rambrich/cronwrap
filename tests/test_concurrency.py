"""Tests for cronwrap.concurrency."""
import json
import os
import time
fport pytest
from pathlib import Path
from unittest.mock import patch

from cronwrap.concurrency import ConcurrencyConfig, ConcurrencyManager, ConcurrencySlotError


@pytest.fixture
def tmp_config(tmp_path):
    return ConcurrencyConfig(enabled=True, max_concurrent=2, state_dir=str(tmp_path), slot_ttl=3600)


def test_config_disabled_by_default():
    cfg = ConcurrencyConfig()
    assert cfg.enabled is False


def test_config_from_env():
    env = {
        "CRONWRAP_CONCURRENCY_ENABLED": "true",
        "CRONWRAP_CONCURRENCY_MAX": "3",
        "CRONWRAP_CONCURRENCY_SLOT_TTL": "600",
    }
    with patch.dict(os.environ, env):
        cfg = ConcurrencyConfig.from_env()
    assert cfg.enabled is True
    assert cfg.max_concurrent == 3
    assert cfg.slot_ttl == 600


def test_acquire_returns_true_when_disabled(tmp_path):
    cfg = ConcurrencyConfig(enabled=False, state_dir=str(tmp_path))
    mgr = ConcurrencyManager(cfg, "job")
    assert mgr.acquire() is True


def test_acquire_succeeds_when_slot_available(tmp_config):
    mgr = ConcurrencyManager(tmp_config, "job")
    assert mgr.acquire() is True
    assert mgr.active_count() == 1
    mgr.release()


def test_acquire_fails_when_slots_full(tmp_config):
    tmp_config.max_concurrent = 1
    mgr1 = ConcurrencyManager(tmp_config, "job")
    mgr2 = ConcurrencyManager(tmp_config, "job")
    with patch("os.getpid", return_value=1001):
        mgr1.acquire()
    with patch("os.getpid", return_value=1002):
        result = mgr2.acquire()
    assert result is False


def test_release_frees_slot(tmp_config):
    tmp_config.max_concurrent = 1
    mgr = ConcurrencyManager(tmp_config, "job")
    mgr.acquire()
    assert mgr.active_count() == 1
    mgr.release()
    assert mgr.active_count() == 0


def test_stale_slots_are_evicted(tmp_config):
    tmp_config.slot_ttl = 1
    path = Path(tmp_config.state_dir) / "job.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    old_slot = [{"pid": 9999, "started_at": time.time() - 10}]
    path.write_text(json.dumps(old_slot))
    mgr = ConcurrencyManager(tmp_config, "job")
    assert mgr.active_count() == 0


def test_active_count_zero_when_disabled(tmp_path):
    cfg = ConcurrencyConfig(enabled=False, state_dir=str(tmp_path))
    mgr = ConcurrencyManager(cfg, "job")
    assert mgr.active_count() == 0
