"""Tests for cronwrap.audit."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.audit import AuditConfig, AuditEntry, AuditLogger
from cronwrap.runner import RunResult


def _make_result(success=True, exit_code=0, duration=1.5):
    r = MagicMock(spec=RunResult)
    r.success = success
    r.exit_code = exit_code
    r.duration = duration
    return r


def test_audit_config_disabled_by_default():
    config = AuditConfig()
    assert config.enabled is False


def test_audit_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_AUDIT_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_AUDIT_LOG", "/tmp/audit.jsonl")
    config = AuditConfig.from_env()
    assert config.enabled is True
    assert config.log_path == "/tmp/audit.jsonl"


def test_record_returns_none_when_disabled():
    logger = AuditLogger(AuditConfig(enabled=False))
    result = logger.record(_make_result(), command="echo hi")
    assert result is None


def test_record_writes_entry(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    config = AuditConfig(enabled=True, log_path=str(log_file))
    logger = AuditLogger(config)
    entry = logger.record(_make_result(success=True, exit_code=0, duration=2.0),
                          command="echo hello", retries=1, tags=["prod"], job_id="job-1")
    assert entry is not None
    assert entry.success is True
    assert entry.retries == 1
    assert log_file.exists()
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["command"] == "echo hello"
    assert data["job_id"] == "job-1"


def test_record_failure_entry(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    config = AuditConfig(enabled=True, log_path=str(log_file))
    logger = AuditLogger(config)
    entry = logger.record(_make_result(success=False, exit_code=1, duration=0.5),
                          command="false")
    assert entry.success is False
    assert entry.exit_code == 1


def test_read_all_returns_entries(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    config = AuditConfig(enabled=True, log_path=str(log_file))
    logger = AuditLogger(config)
    logger.record(_make_result(), command="cmd1")
    logger.record(_make_result(success=False, exit_code=2), command="cmd2")
    entries = logger.read_all()
    assert len(entries) == 2
    assert entries[0].command == "cmd1"
    assert entries[1].command == "cmd2"


def test_read_all_empty_when_no_file(tmp_path):
    config = AuditConfig(enabled=True, log_path=str(tmp_path / "missing.jsonl"))
    logger = AuditLogger(config)
    assert logger.read_all() == []
