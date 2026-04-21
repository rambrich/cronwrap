"""Tests for cronwrap.fingerprint."""
import os
import socket
from unittest.mock import patch

import pytest

from cronwrap.fingerprint import FingerprintConfig, FingerprintManager


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_fingerprint_config_enabled_by_default():
    cfg = FingerprintConfig()
    assert cfg.enabled is True


def test_fingerprint_config_from_env_disabled(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FINGERPRINT_ENABLED", "false")
    cfg = FingerprintConfig.from_env()
    assert cfg.enabled is False


def test_fingerprint_config_from_env_no_hostname(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FINGERPRINT_HOSTNAME", "false")
    cfg = FingerprintConfig.from_env()
    assert cfg.include_hostname is False


def test_fingerprint_config_extra_fields_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FINGERPRINT_EXTRA", "env=prod,region=us-east")
    cfg = FingerprintConfig.from_env()
    assert cfg.extra_fields == {"env": "prod", "region": "us-east"}


def test_fingerprint_config_extra_fields_empty(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FINGERPRINT_EXTRA", "")
    cfg = FingerprintConfig.from_env()
    assert cfg.extra_fields == {}


# ---------------------------------------------------------------------------
# Manager tests
# ---------------------------------------------------------------------------

def test_generate_returns_none_when_disabled():
    cfg = FingerprintConfig(enabled=False)
    mgr = FingerprintManager(config=cfg)
    result = mgr.generate("echo hello")
    assert result is None


def test_generate_returns_fingerprint():
    cfg = FingerprintConfig(enabled=True, include_hostname=False, include_user=False)
    mgr = FingerprintManager(config=cfg)
    fp = mgr.generate("echo hello")
    assert fp is not None
    assert fp.command == "echo hello"
    assert len(fp.digest) == 16


def test_generate_digest_is_deterministic():
    cfg = FingerprintConfig(enabled=True, include_hostname=False, include_user=False)
    mgr = FingerprintManager(config=cfg)
    fp1 = mgr.generate("echo hello")
    fp2 = mgr.generate("echo hello")
    assert fp1.digest == fp2.digest


def test_generate_digest_differs_by_command():
    cfg = FingerprintConfig(enabled=True, include_hostname=False, include_user=False)
    mgr = FingerprintManager(config=cfg)
    fp1 = mgr.generate("echo hello")
    fp2 = mgr.generate("echo world")
    assert fp1.digest != fp2.digest


def test_generate_includes_hostname():
    cfg = FingerprintConfig(enabled=True, include_hostname=True, include_user=False)
    mgr = FingerprintManager(config=cfg)
    fp = mgr.generate("echo hello")
    assert "hostname" in fp.components
    assert fp.components["hostname"] == socket.gethostname()


def test_generate_includes_run_id():
    cfg = FingerprintConfig(enabled=True, include_hostname=False, include_user=False)
    mgr = FingerprintManager(config=cfg)
    fp = mgr.generate("echo hello", run_id="abc-123")
    assert fp.components.get("run_id") == "abc-123"


def test_generate_run_id_changes_digest():
    cfg = FingerprintConfig(enabled=True, include_hostname=False, include_user=False)
    mgr = FingerprintManager(config=cfg)
    fp1 = mgr.generate("echo hello", run_id="run-1")
    fp2 = mgr.generate("echo hello", run_id="run-2")
    assert fp1.digest != fp2.digest
