"""Tests for cronwrap.metadata."""
import pytest
from unittest.mock import patch
from cronwrap.metadata import MetadataConfig, MetadataManager, RunMetadata


def test_metadata_config_enabled_by_default():
    cfg = MetadataConfig()
    assert cfg.enabled is True


def test_metadata_config_from_env_disabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_METADATA_ENABLED", "false")
    cfg = MetadataConfig.from_env()
    assert cfg.enabled is False


def test_metadata_config_from_env_enabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_METADATA_ENABLED", "true")
    cfg = MetadataConfig.from_env()
    assert cfg.enabled is True


def test_metadata_config_extra_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_METADATA_EXTRA", "env=prod,region=us-east")
    cfg = MetadataConfig.from_env()
    assert cfg.extra == {"env": "prod", "region": "us-east"}


def test_metadata_config_extra_empty(monkeypatch):
    monkeypatch.delenv("CRONWRAP_METADATA_EXTRA", raising=False)
    cfg = MetadataConfig.from_env()
    assert cfg.extra == {}


def test_collect_returns_none_when_disabled():
    cfg = MetadataConfig(enabled=False)
    mgr = MetadataManager(cfg)
    assert mgr.collect() is None


def test_collect_returns_metadata_when_enabled():
    cfg = MetadataConfig(enabled=True)
    mgr = MetadataManager(cfg)
    result = mgr.collect()
    assert isinstance(result, RunMetadata)


def test_collect_includes_hostname():
    cfg = MetadataConfig(enabled=True, include_hostname=True)
    mgr = MetadataManager(cfg)
    with patch("cronwrap.metadata.socket.gethostname", return_value="test-host"):
        result = mgr.collect()
    assert result is not None
    assert result.hostname == "test-host"


def test_collect_excludes_hostname_when_disabled():
    cfg = MetadataConfig(enabled=True, include_hostname=False)
    mgr = MetadataManager(cfg)
    result = mgr.collect()
    assert result is not None
    assert result.hostname is None


def test_collect_includes_user():
    cfg = MetadataConfig(enabled=True, include_user=True)
    mgr = MetadataManager(cfg)
    with patch("cronwrap.metadata.getpass.getuser", return_value="cron-user"):
        result = mgr.collect()
    assert result is not None
    assert result.user == "cron-user"


def test_collect_excludes_user_when_disabled():
    cfg = MetadataConfig(enabled=True, include_user=False)
    mgr = MetadataManager(cfg)
    result = mgr.collect()
    assert result is not None
    assert result.user is None


def test_collect_includes_extra():
    cfg = MetadataConfig(enabled=True, extra={"env": "staging"})
    mgr = MetadataManager(cfg)
    result = mgr.collect()
    assert result is not None
    assert result.extra == {"env": "staging"}


def test_to_dict_excludes_none_fields():
    meta = RunMetadata(hostname=None, user=None, extra={})
    d = meta.to_dict()
    assert "hostname" not in d
    assert "user" not in d


def test_to_dict_includes_set_fields():
    meta = RunMetadata(hostname="h1", user="u1", extra={"k": "v"})
    d = meta.to_dict()
    assert d["hostname"] == "h1"
    assert d["user"] == "u1"
    assert d["extra"] == {"k": "v"}
