"""Tests for cronwrap.dependency."""
import os
import pytest
from unittest.mock import patch
from cronwrap.dependency import DependencyConfig, DependencyChecker, MissingDependencyError


def test_config_disabled_by_default():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("CRONWRAP_DEP_CHECK", None)
        cfg = DependencyConfig.from_env()
        assert cfg.enabled is False


def test_config_from_env():
    with patch.dict(os.environ, {
        "CRONWRAP_DEP_CHECK": "1",
        "CRONWRAP_DEP_COMMANDS": "bash,curl",
        "CRONWRAP_DEP_ENV_VARS": "HOME,PATH",
    }):
        cfg = DependencyConfig.from_env()
        assert cfg.enabled is True
        assert "bash" in cfg.commands
        assert "curl" in cfg.commands
        assert "HOME" in cfg.env_vars


def test_check_returns_none_when_disabled():
    cfg = DependencyConfig(enabled=False, commands=["nonexistent_xyz"])
    checker = DependencyChecker(cfg)
    assert checker.check() is None


def test_check_passes_when_all_present():
    cfg = DependencyConfig(enabled=True, commands=["python3"], env_vars=["PATH"])
    checker = DependencyChecker(cfg)
    result = checker.check()
    assert result is None


def test_check_detects_missing_command():
    cfg = DependencyConfig(enabled=True, commands=["__no_such_cmd_xyz__"])
    checker = DependencyChecker(cfg)
    result = checker.check()
    assert result is not None
    assert "__no_such_cmd_xyz__" in result.missing_commands


def test_check_detects_missing_env_var():
    cfg = DependencyConfig(enabled=True, env_vars=["__NO_SUCH_VAR_XYZ__"])
    checker = DependencyChecker(cfg)
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("__NO_SUCH_VAR_XYZ__", None)
        result = checker.check()
    assert result is not None
    assert "__NO_SUCH_VAR_XYZ__" in result.missing_env_vars


def test_missing_dependency_error_str():
    err = MissingDependencyError(missing_commands=["curl"], missing_env_vars=["TOKEN"])
    s = str(err)
    assert "curl" in s
    assert "TOKEN" in s


def test_missing_dependency_error_bool_false_when_empty():
    err = MissingDependencyError()
    assert not err
