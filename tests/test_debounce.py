"""Tests for cronwrap.debounce."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.debounce import DebounceConfig, DebounceManager


@pytest.fixture()
def tmp_config(tmp_path):
    return DebounceConfig(enabled=True, min_interval=60, state_dir=str(tmp_path))


def test_debounce_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        cfg = DebounceConfig.from_env()
    assert cfg.enabled is False


def test_debounce_config_from_env():
    env = {
        "CRONWRAP_DEBOUNCE_ENABLED": "true",
        "CRONWRAP_DEBOUNCE_INTERVAL": "120",
    }
    with patch.dict("os.environ", env, clear=True):
        cfg = DebounceConfig.from_env()
    assert cfg.enabled is True
    assert cfg.min_interval == 120


def test_should_skip_false_when_disabled(tmp_path):
    cfg = DebounceConfig(enabled=False, min_interval=60, state_dir=str(tmp_path))
    mgr = DebounceManager(cfg)
    assert mgr.should_skip("myjob") is False


def test_should_skip_false_when_no_state(tmp_config):
    mgr = DebounceManager(tmp_config)
    assert mgr.should_skip("myjob") is False


def test_should_skip_true_when_ran_recently(tmp_config):
    mgr = DebounceManager(tmp_config)
    mgr.record("myjob")
    assert mgr.should_skip("myjob") is True


def test_should_skip_false_when_interval_elapsed(tmp_config, tmp_path):
    mgr = DebounceManager(tmp_config)
    old_ts = time.time() - 120  # older than min_interval=60
    state_file = tmp_path / "myjob.json"
    state_file.write_text(json.dumps({"last_run": old_ts}))
    assert mgr.should_skip("myjob") is False


def test_record_noop_when_disabled(tmp_path):
    cfg = DebounceConfig(enabled=False, state_dir=str(tmp_path))
    mgr = DebounceManager(cfg)
    mgr.record("myjob")
    assert not (tmp_path / "myjob.json").exists()


def test_record_writes_state(tmp_config, tmp_path):
    mgr = DebounceManager(tmp_config)
    before = time.time()
    mgr.record("myjob")
    after = time.time()
    data = json.loads((tmp_path / "myjob.json").read_text())
    assert before <= data["last_run"] <= after
