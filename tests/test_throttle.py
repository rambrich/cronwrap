"""Tests for cronwrap.throttle."""
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.throttle import Throttle, ThrottleConfig


@pytest.fixture
def tmp_config(tmp_path):
    return ThrottleConfig(enabled=True, window_seconds=3600, max_runs=2, state_dir=str(tmp_path))


def test_throttle_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        cfg = ThrottleConfig.from_env()
    assert cfg.enabled is False


def test_throttle_config_from_env(tmp_path):
    env = {
        "CRONWRAP_THROTTLE_ENABLED": "true",
        "CRONWRAP_THROTTLE_WINDOW": "1800",
        "CRONWRAP_THROTTLE_MAX_RUNS": "3",
        "CRONWRAP_THROTTLE_STATE_DIR": str(tmp_path),
    }
    with patch.dict("os.environ", env, clear=True):
        cfg = ThrottleConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 1800
    assert cfg.max_runs == 3


def test_allowed_when_disabled(tmp_path):
    cfg = ThrottleConfig(enabled=False, state_dir=str(tmp_path))
    t = Throttle(cfg, "myjob")
    assert t.check() is True


def test_allowed_when_no_runs(tmp_config):
    t = Throttle(tmp_config, "myjob")
    assert t.check() is True


def test_record_increments_count(tmp_config):
    t = Throttle(tmp_config, "myjob")
    t.record()
    assert t.run_count_in_window() == 1


def test_throttled_after_max_runs(tmp_config):
    t = Throttle(tmp_config, "myjob")
    t.record()
    t.record()
    assert t.check() is False


def test_old_runs_pruned(tmp_path):
    cfg = ThrottleConfig(enabled=True, window_seconds=10, max_runs=1, state_dir=str(tmp_path))
    t = Throttle(cfg, "myjob")
    old_ts = time.time() - 20
    state_path = Path(tmp_path) / "myjob.json"
    state_path.write_text(json.dumps({"runs": [old_ts]}))
    assert t.check() is True
    assert t.run_count_in_window() == 0


def test_record_noop_when_disabled(tmp_path):
    cfg = ThrottleConfig(enabled=False, state_dir=str(tmp_path))
    t = Throttle(cfg, "myjob")
    t.record()
    state_path = Path(tmp_path) / "myjob.json"
    assert not state_path.exists()
