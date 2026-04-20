"""Structured event log for cronwrap run lifecycle events."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class EventLogConfig:
    enabled: bool = False
    log_dir: str = "/tmp/cronwrap/events"
    max_events: int = 500

    @classmethod
    def from_env(cls) -> "EventLogConfig":
        enabled = os.environ.get("CRONWRAP_EVENTLOG_ENABLED", "").lower() in ("1", "true")
        log_dir = os.environ.get("CRONWRAP_EVENTLOG_DIR", "/tmp/cronwrap/events")
        try:
            max_events = int(os.environ.get("CRONWRAP_EVENTLOG_MAX_EVENTS", "500"))
        except ValueError:
            max_events = 500
        return cls(enabled=enabled, log_dir=log_dir, max_events=max_events)


@dataclass
class EventEntry:
    event: str
    command: str
    timestamp: float = field(default_factory=time.time)
    exit_code: Optional[int] = None
    duration: Optional[float] = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "event": self.event,
            "command": self.command,
            "timestamp": self.timestamp,
            "exit_code": self.exit_code,
            "duration": self.duration,
            "detail": self.detail,
        }


class EventLogger:
    def __init__(self, config: EventLogConfig) -> None:
        self.config = config

    def _log_path(self, command: str) -> Path:
        safe = command.replace("/", "_").replace(" ", "_")[:48]
        return Path(self.config.log_dir) / f"{safe}.jsonl"

    def record(self, event: str, result: RunResult, detail: str = "") -> Optional[EventEntry]:
        if not self.config.enabled:
            return None
        entry = EventEntry(
            event=event,
            command=result.command,
            exit_code=result.exit_code,
            duration=result.duration,
            detail=detail,
        )
        path = self._log_path(result.command)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: List[str] = []
        if path.exists():
            lines = path.read_text().splitlines()
        lines.append(json.dumps(entry.to_dict()))
        lines = lines[-self.config.max_events :]
        path.write_text("\n".join(lines) + "\n")
        return entry

    def load(self, command: str) -> List[EventEntry]:
        if not self.config.enabled:
            return []
        path = self._log_path(command)
        if not path.exists():
            return []
        entries = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                entries.append(
                    EventEntry(
                        event=d["event"],
                        command=d["command"],
                        timestamp=d["timestamp"],
                        exit_code=d.get("exit_code"),
                        duration=d.get("duration"),
                        detail=d.get("detail", ""),
                    )
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return entries
