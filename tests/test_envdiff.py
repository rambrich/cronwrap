"""Tests for cronwrap.envdiff."""
import json
import os
from pathlib import Path

import pytest

from cronwrap.envdiff import EnvDiffConfig, EnvDiffManager, EnvDiffResult


@pytest.fixture
def tmp_config(tmp_path):
    return EnvDiffConfig(enabled=True, state_dir=str(tmp_path), tracked_vars=[])


def test_envdiff_config_disabled_by_default():
    cfg = EnvDiffConfig()
    assert cfg.enabled is False


def test_envdiff_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_ENVDIFF_ENABLED", "1")
    monkeypatch.setenv("CRONWRAP_ENVDIFF_VARS", "PATH,HOME")
    cfg = EnvDiffConfig.from_env()
    assert cfg.enabled is True
    assert "PATH" in cfg.tracked_vars
    assert "HOME" in cfg.tracked_vars


def test_diff_returns_none_when_disabled(tmp_path):
    cfg = EnvDiffConfig(enabled=False, state_dir=str(tmp_path))
    mgr = EnvDiffManager(cfg, job_id="test")
    assert mgr.diff() is None


def test_diff_returns_empty_on_first_run(tmp_config):
    mgr = EnvDiffManager(tmp_config, job_id="first")
    result = mgr.diff()
    assert isinstance(result, EnvDiffResult)
    assert not result.has_changes


def test_diff_detects_added_var(tmp_config, monkeypatch):
    tmp_config.tracked_vars = ["MY_VAR"]
    mgr = EnvDiffManager(tmp_config, job_id="added")
    # First run: MY_VAR absent
    monkeypatch.delenv("MY_VAR", raising=False)
    mgr.diff()
    # Second run: MY_VAR present
    monkeypatch.setenv("MY_VAR", "hello")
    result = mgr.diff()
    assert "MY_VAR" in result.added
    assert result.has_changes


def test_diff_detects_removed_var(tmp_config, monkeypatch):
    tmp_config.tracked_vars = ["MY_VAR"]
    mgr = EnvDiffManager(tmp_config, job_id="removed")
    monkeypatch.setenv("MY_VAR", "hello")
    mgr.diff()
    monkeypatch.delenv("MY_VAR")
    result = mgr.diff()
    assert "MY_VAR" in result.removed
    assert result.has_changes


def test_diff_detects_changed_var(tmp_config, monkeypatch):
    tmp_config.tracked_vars = ["MY_VAR"]
    mgr = EnvDiffManager(tmp_config, job_id="changed")
    monkeypatch.setenv("MY_VAR", "old")
    mgr.diff()
    monkeypatch.setenv("MY_VAR", "new")
    result = mgr.diff()
    assert "MY_VAR" in result.changed
    assert result.changed["MY_VAR"] == ("old", "new")


def test_diff_to_dict_structure(tmp_config, monkeypatch):
    tmp_config.tracked_vars = ["MY_VAR"]
    mgr = EnvDiffManager(tmp_config, job_id="dict")
    monkeypatch.setenv("MY_VAR", "v1")
    mgr.diff()
    monkeypatch.setenv("MY_VAR", "v2")
    result = mgr.diff()
    d = result.to_dict()
    assert "added" in d and "removed" in d and "changed" in d
    assert d["changed"]["MY_VAR"] == {"before": "v1", "after": "v2"}


def test_reset_removes_state(tmp_config, monkeypatch):
    tmp_config.tracked_vars = ["MY_VAR"]
    monkeypatch.setenv("MY_VAR", "x")
    mgr = EnvDiffManager(tmp_config, job_id="reset")
    mgr.diff()
    state_path = Path(tmp_config.state_dir) / "reset.json"
    assert state_path.exists()
    mgr.reset()
    assert not state_path.exists()
