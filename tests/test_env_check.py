import os
import pytest
from cronwrap.env_check import EnvCheckConfig, EnvChecker, MissingVarsError


def test_env_check_config_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CRONWRAP_REQUIRED_ENV", raising=False)
    cfg = EnvCheckConfig.from_env()
    assert cfg.enabled is False
    assert cfg.required_vars == []


def test_env_check_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_REQUIRED_ENV", "FOO,BAR,BAZ")
    cfg = EnvCheckConfig.from_env()
    assert cfg.enabled is True
    assert cfg.required_vars == ["FOO", "BAR", "BAZ"]


def test_check_returns_none_when_disabled(monkeypatch):
    cfg = EnvCheckConfig(enabled=False, required_vars=["MISSING_VAR"])
    checker = EnvChecker(cfg)
    assert checker.check() is None


def test_check_returns_none_when_all_present(monkeypatch):
    monkeypatch.setenv("MY_VAR", "hello")
    cfg = EnvCheckConfig(enabled=True, required_vars=["MY_VAR"])
    checker = EnvChecker(cfg)
    assert checker.check() is None


def test_check_returns_error_for_missing(monkeypatch):
    monkeypatch.delenv("DEFINITELY_MISSING", raising=False)
    cfg = EnvCheckConfig(enabled=True, required_vars=["DEFINITELY_MISSING"])
    checker = EnvChecker(cfg)
    err = checker.check()
    assert isinstance(err, MissingVarsError)
    assert "DEFINITELY_MISSING" in err.missing


def test_assert_ok_raises_on_missing(monkeypatch):
    monkeypatch.delenv("ABSENT_VAR", raising=False)
    cfg = EnvCheckConfig(enabled=True, required_vars=["ABSENT_VAR"])
    checker = EnvChecker(cfg)
    with pytest.raises(MissingVarsError) as exc_info:
        checker.assert_ok()
    assert "ABSENT_VAR" in str(exc_info.value)


def test_assert_ok_passes_when_all_present(monkeypatch):
    monkeypatch.setenv("PRESENT_VAR", "value")
    cfg = EnvCheckConfig(enabled=True, required_vars=["PRESENT_VAR"])
    checker = EnvChecker(cfg)
    checker.assert_ok()  # should not raise
