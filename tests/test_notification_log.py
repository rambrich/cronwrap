"""Tests for cronwrap.notification_log."""
import json
import pytest
from cronwrap.notification_log import (
    NotificationLogConfig,
    NotificationEntry,
    NotificationLogger,
)


@pytest.fixture
def tmp_config(tmp_path):
    return NotificationLogConfig(enabled=True, log_dir=str(tmp_path))


def _entry(**kwargs) -> NotificationEntry:
    defaults = dict(
        job_name="backup",
        channel="email",
        event="failure",
        recipient="ops@example.com",
    )
    defaults.update(kwargs)
    return NotificationEntry(**defaults)


def test_config_disabled_by_default():
    cfg = NotificationLogConfig()
    assert cfg.enabled is False


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_NOTIF_LOG_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_NOTIF_LOG_DIR", "/var/log/cw")
    cfg = NotificationLogConfig.from_env()
    assert cfg.enabled is True
    assert cfg.log_dir == "/var/log/cw"


def test_record_returns_none_when_disabled(tmp_path):
    cfg = NotificationLogConfig(enabled=False, log_dir=str(tmp_path))
    logger = NotificationLogger(cfg)
    result = logger.record(_entry())
    assert result is None


def test_record_writes_entry(tmp_config):
    logger = NotificationLogger(tmp_config)
    e = _entry()
    returned = logger.record(e)
    assert returned is not None
    path = logger._log_path("backup")
    assert path.exists()
    data = json.loads(path.read_text().strip())
    assert data["channel"] == "email"
    assert data["event"] == "failure"


def test_load_returns_empty_when_disabled(tmp_path):
    cfg = NotificationLogConfig(enabled=False, log_dir=str(tmp_path))
    logger = NotificationLogger(cfg)
    assert logger.load("backup") == []


def test_load_returns_entries(tmp_config):
    logger = NotificationLogger(tmp_config)
    logger.record(_entry(event="failure"))
    logger.record(_entry(event="success", channel="webhook"))
    entries = logger.load("backup")
    assert len(entries) == 2
    assert entries[0].event == "failure"
    assert entries[1].channel == "webhook"


def test_entry_to_dict_roundtrip():
    e = _entry(success=False, error="smtp timeout")
    d = e.to_dict()
    e2 = NotificationEntry.from_dict(d)
    assert e2.error == "smtp timeout"
    assert e2.success is False


def test_load_returns_empty_when_no_file(tmp_config):
    logger = NotificationLogger(tmp_config)
    result = logger.load("nonexistent_job")
    assert result == []
