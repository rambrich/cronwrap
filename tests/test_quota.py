"""Tests for cronwrap.quota."""
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.quota import QuotaConfig, QuotaManager


@pytest.fixture
def cfg(tmp_path):
    return QuotaConfig(enabled=True, period="daily", max_runs=2, state_dir=str(tmp_path))


def test_quota_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        c = QuotaConfig.from_env()
    assert c.enabled is False


def test_quota_config_from_env(tmp_path):
    env = {
        "CRONWRAP_QUOTA_ENABLED": "true",
        "CRONWRAP_QUOTA_PERIOD": "weekly",
        "CRONWRAP_QUOTA_MAX_RUNS": "5",
        "CRONWRAP_QUOTA_STATE_DIR": str(tmp_path),
    }
    with patch.dict("os.environ", env, clear=True):
        c = QuotaConfig.from_env()
    assert c.enabled is True
    assert c.period == "weekly"
    assert c.max_runs == 5
    assert c.window_seconds == 604800


def test_within_quota_when_disabled(tmp_path):
    c = QuotaConfig(enabled=False, state_dir=str(tmp_path))
    qm = QuotaManager(c, "job")
    assert qm.within_quota() is True


def test_within_quota_initially(cfg):
    qm = QuotaManager(cfg, "job")
    assert qm.within_quota() is True


def test_consume_returns_true_within_quota(cfg):
    qm = QuotaManager(cfg, "job")
    assert qm.consume() is True
    assert qm.remaining() == 1


def test_consume_returns_false_when_exceeded(cfg):
    qm = QuotaManager(cfg, "job")
    qm.consume()
    qm.consume()
    assert qm.consume() is False


def test_remaining_decrements(cfg):
    qm = QuotaManager(cfg, "job")
    assert qm.remaining() == 2
    qm.consume()
    assert qm.remaining() == 1


def test_expired_runs_not_counted(tmp_path):
    c = QuotaConfig(enabled=True, period="hourly", max_runs=1, state_dir=str(tmp_path))
    qm = QuotaManager(c, "job")
    old = time.time() - 7200
    p = Path(tmp_path) / "job_quota.json"
    p.write_text(json.dumps({"runs": [old]}))
    assert qm.within_quota() is True
    assert qm.remaining() == 1
