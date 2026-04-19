"""Concurrency limiting for cronwrap — cap simultaneous runs across jobs."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ConcurrencyConfig:
    enabled: bool = False
    max_concurrent: int = 1
    state_dir: str = "/tmp/cronwrap/concurrency"
    slot_ttl: int = 3600  # seconds before a slot is considered stale

    @classmethod
    def from_env(cls) -> "ConcurrencyConfig":
        enabled = os.environ.get("CRONWRAP_CONCURRENCY_ENABLED", "").lower() == "true"
        max_concurrent = int(os.environ.get("CRONWRAP_CONCURRENCY_MAX", "1"))
        state_dir = os.environ.get("CRONWRAP_CONCURRENCY_STATE_DIR", "/tmp/cronwrap/concurrency")
        slot_ttl = int(os.environ.get("CRONWRAP_CONCURRENCY_SLOT_TTL", "3600"))
        return cls(enabled=enabled, max_concurrent=max_concurrent, state_dir=state_dir, slot_ttl=slot_ttl)


class ConcurrencySlotError(Exception):
    """Raised when no concurrency slot is available."""


class ConcurrencyManager:
    def __init__(self, config: ConcurrencyConfig, job_name: str = "default") -> None:
        self.config = config
        self.job_name = job_name
        self._slot_file: Optional[Path] = None

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_name}.json"

    def _load_slots(self) -> list:
        path = self._state_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            now = time.time()
            return [s for s in data if now - s["started_at"] < self.config.slot_ttl]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_slots(self, slots: list) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(slots))

    def acquire(self) -> bool:
        """Try to acquire a concurrency slot. Returns True if acquired."""
        if not self.config.enabled:
            return True
        slots = self._load_slots()
        if len(slots) >= self.config.max_concurrent:
            return False
        entry = {"pid": os.getpid(), "started_at": time.time()}
        slots.append(entry)
        self._save_slots(slots)
        self._slot_file = self._state_path()
        self._slot_pid = entry["pid"]
        return True

    def release(self) -> None:
        """Release the held concurrency slot."""
        if not self.config.enabled:
            return
        slots = self._load_slots()
        pid = os.getpid()
        slots = [s for s in slots if s.get("pid") != pid]
        self._save_slots(slots)

    def active_count(self) -> int:
        if not self.config.enabled:
            return 0
        return len(self._load_slots())
