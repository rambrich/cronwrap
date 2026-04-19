"""Dead-letter queue: persist failed run results for later inspection or replay."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class DeadLetterConfig:
    enabled: bool = False
    directory: str = "/tmp/cronwrap/deadletter"
    max_entries: int = 100

    @staticmethod
    def from_env() -> "DeadLetterConfig":
        enabled = os.environ.get("CRONWRAP_DEADLETTER_ENABLED", "").lower() in ("1", "true")
        directory = os.environ.get("CRONWRAP_DEADLETTER_DIR", "/tmp/cronwrap/deadletter")
        try:
            max_entries = int(os.environ.get("CRONWRAP_DEADLETTER_MAX", "100"))
        except ValueError:
            max_entries = 100
        return DeadLetterConfig(enabled=enabled, directory=directory, max_entries=max_entries)


@dataclass
class DeadLetterEntry:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(d: dict) -> "DeadLetterEntry":
        return DeadLetterEntry(**d)


class DeadLetterQueue:
    def __init__(self, config: DeadLetterConfig):
        self.config = config
        if config.enabled:
            Path(config.directory).mkdir(parents=True, exist_ok=True)

    def push(self, result: RunResult) -> Optional[Path]:
        if not self.config.enabled or result.success:
            return None
        entry = DeadLetterEntry(
            command=result.command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=result.duration,
        )
        path = Path(self.config.directory) / f"{int(entry.timestamp * 1000)}.json"
        path.write_text(json.dumps(entry.to_dict(), indent=2))
        self._evict()
        return path

    def list_entries(self) -> List[DeadLetterEntry]:
        d = Path(self.config.directory)
        if not d.exists():
            return []
        entries = []
        for f in sorted(d.glob("*.json")):
            try:
                entries.append(DeadLetterEntry.from_dict(json.loads(f.read_text())))
            except Exception:
                pass
        return entries

    def clear(self) -> int:
        d = Path(self.config.directory)
        if not d.exists():
            return 0
        removed = 0
        for f in d.glob("*.json"):
            f.unlink()
            removed += 1
        return removed

    def _evict(self) -> None:
        d = Path(self.config.directory)
        files = sorted(d.glob("*.json"))
        while len(files) > self.config.max_entries:
            files.pop(0).unlink()
