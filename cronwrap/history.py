"""Run history storage for cronwrap — persists run results to a JSON file."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class HistoryConfig:
    enabled: bool = False
    history_file: str = "/var/log/cronwrap_history.json"
    max_entries: int = 100

    @classmethod
    def from_env(cls) -> "HistoryConfig":
        enabled = os.environ.get("CRONWRAP_HISTORY_ENABLED", "").lower() in ("1", "true", "yes")
        history_file = os.environ.get("CRONWRAP_HISTORY_FILE", "/var/log/cronwrap_history.json")
        max_entries = int(os.environ.get("CRONWRAP_HISTORY_MAX_ENTRIES", "100"))
        return cls(enabled=enabled, history_file=history_file, max_entries=max_entries)


@dataclass
class HistoryEntry:
    job_name: str
    command: str
    success: bool
    exit_code: int
    duration_seconds: float
    timestamp: str
    stdout: str = ""
    stderr: str = ""


class HistoryStore:
    def __init__(self, config: HistoryConfig) -> None:
        self.config = config

    def record(self, job_name: str, result: RunResult) -> Optional[HistoryEntry]:
        if not self.config.enabled:
            return None

        entry = HistoryEntry(
            job_name=job_name,
            command=result.command,
            success=result.success,
            exit_code=result.exit_code,
            duration_seconds=round(result.duration, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )
        self._append(entry)
        return entry

    def _append(self, entry: HistoryEntry) -> None:
        path = Path(self.config.history_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        entries: List[dict] = []
        if path.exists():
            try:
                entries = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                entries = []

        entries.append(asdict(entry))
        entries = entries[-self.config.max_entries :]
        path.write_text(json.dumps(entries, indent=2))

    def load(self) -> List[HistoryEntry]:
        path = Path(self.config.history_file)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text())
            return [HistoryEntry(**r) for r in raw]
        except (json.JSONDecodeError, OSError, TypeError):
            return []
