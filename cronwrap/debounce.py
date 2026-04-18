"""Debounce: skip a run if the same job ran too recently."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DebounceConfig:
    enabled: bool = False
    min_interval: int = 60  # seconds
    state_dir: str = "/tmp/cronwrap/debounce"

    @classmethod
    def from_env(cls) -> "DebounceConfig":
        enabled = os.environ.get("CRONWRAP_DEBOUNCE_ENABLED", "").lower() == "true"
        interval = int(os.environ.get("CRONWRAP_DEBOUNCE_INTERVAL", "60"))
        state_dir = os.environ.get("CRONWRAP_DEBOUNCE_STATE_DIR", "/tmp/cronwrap/debounce")
        return cls(enabled=enabled, min_interval=interval, state_dir=state_dir)


class DebounceManager:
    def __init__(self, config: DebounceConfig) -> None:
        self.config = config

    def _state_path(self, job_id: str) -> Path:
        return Path(self.config.state_dir) / f"{job_id}.json"

    def _load_last_run(self, job_id: str) -> Optional[float]:
        path = self._state_path(job_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return float(data.get("last_run", 0))
        except (ValueError, KeyError, json.JSONDecodeError):
            return None

    def _save_last_run(self, job_id: str, ts: float) -> None:
        path = self._state_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_run": ts}))

    def should_skip(self, job_id: str) -> bool:
        """Return True if the job ran too recently and should be skipped."""
        if not self.config.enabled:
            return False
        last = self._load_last_run(job_id)
        if last is None:
            return False
        return (time.time() - last) < self.config.min_interval

    def record(self, job_id: str) -> None:
        """Record that the job ran right now."""
        if not self.config.enabled:
            return
        self._save_last_run(job_id, time.time())
