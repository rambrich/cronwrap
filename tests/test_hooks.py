"""Tests for cronwrap.hooks."""
import os
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.hooks import HookManager, HooksConfig, _run_hook
from cronwrap.runner import RunResult


def _make_result(exit_code: int = 0, duration: float = 1.0) -> RunResult:
    return RunResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="hi",
        stderr="",
        duration=duration,
        timed_out=False,
    )


def test_hooks_config_disabled_by_default():
    config = HooksConfig.from_env({})
    assert config.enabled is True
    assert config.pre_hooks == []
    assert config.post_hooks == []


def test_hooks_config_from_env():
    env = {
        "CRONWRAP_PRE_HOOKS": "echo pre1, echo pre2",
        "CRONWRAP_POST_HOOKS": "echo post1",
        "CRONWRAP_HOOKS_ENABLED": "true",
    }
    config = HooksConfig.from_env(env)
    assert config.pre_hooks == ["echo pre1", "echo pre2"]
    assert config.post_hooks == ["echo post1"]
    assert config.enabled is True


def test_hooks_config_disabled_via_env():
    config = HooksConfig.from_env({"CRONWRAP_HOOKS_ENABLED": "false"})
    assert config.enabled is False


def test_run_pre_hooks_returns_empty_when_disabled():
    config = HooksConfig(pre_hooks=["echo hi"], enabled=False)
    manager = HookManager(config=config)
    assert manager.run_pre_hooks() == []


def test_run_post_hooks_returns_empty_when_disabled():
    config = HooksConfig(post_hooks=["echo hi"], enabled=False)
    manager = HookManager(config=config)
    assert manager.run_post_hooks(_make_result()) == []


def test_run_pre_hooks_success():
    config = HooksConfig(pre_hooks=["echo ok"], enabled=True)
    manager = HookManager(config=config)
    results = manager.run_pre_hooks()
    assert results == [True]


def test_run_post_hooks_success():
    config = HooksConfig(post_hooks=["echo ok"], enabled=True)
    manager = HookManager(config=config)
    results = manager.run_post_hooks(_make_result())
    assert results == [True]


def test_run_hook_failure_returns_false():
    result = _run_hook("exit 1", timeout=5)
    assert result is False


def test_run_hook_timeout_returns_false():
    with patch("cronwrap.hooks.subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("cmd", 1)):
        result = _run_hook("sleep 100", timeout=1)
    assert result is False
