"""Notification log — persists a record of every alert/notification sent."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class NotificationLogConfig:
    enabled: bool = False
    log_dir: str = "/tmp/cronwrap/notification_log"

    @classmethod
    def from_env(cls) -> "NotificationLogConfig":
        enabled = os.environ.get("CRONWRAP_NOTIF_LOG_ENABLED", "").lower() in ("1", "true", "yes")
        log_dir = os.environ.get("CRONWRAP_NOTIF_LOG_DIR", "/tmp/cronwrap/notification_log")
        return cls(enabled=enabled, log_dir=log_dir)


@dataclass
class NotificationEntry:
    job_name: str
    channel: str          # e.g. "email", "webhook", "slack"
    event: str            # e.g. "failure", "success"
    recipient: str
    sent_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "channel": self.channel,
            "event": self.event,
            "recipient": self.recipient,
            "sent_at": self.sent_at,
            "success": self.success,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationEntry":
        return cls(**data)


class NotificationLogger:
    def __init__(self, config: NotificationLogConfig) -> None:
        self.config = config

    def _log_path(self, job_name: str) -> Path:
        safe = job_name.replace(" ", "_").replace("/", "_")
        return Path(self.config.log_dir) / f"{safe}.jsonl"

    def record(self, entry: NotificationEntry) -> Optional[NotificationEntry]:
        if not self.config.enabled:
            return None
        path = self._log_path(entry.job_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
        return entry

    def load(self, job_name: str) -> List[NotificationEntry]:
        if not self.config.enabled:
            return []
        path = self._log_path(job_name)
        if not path.exists():
            return []
        entries: List[NotificationEntry] = []
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(NotificationEntry.from_dict(json.loads(line)))
        return entries
