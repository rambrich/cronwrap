"""Throttle: limit how often a job can run within a time window."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ThrottleConfig:
    enabled: bool = False
    window_seconds: int = 3600
    max_runs: int = 1
    state_dir: str = "/tmp/cronwrap/throttle"

    @classmethod
    def from_env(cls) -> "ThrottleConfig":
        enabled = os.environ.get("CRONWRAP_THROTTLE_ENABLED", "").lower() == "true"
        window = int(os.environ.get("CRONWRAP_THROTTLE_WINDOW", "3600"))
        max_runs = int(os.environ.get("CRONWRAP_THROTTLE_MAX_RUNS", "1"))
        state_dir = os.environ.get("CRONWRAP_THROTTLE_STATE_DIR", "/tmp/cronwrap/throttle")
        return cls(enabled=enabled, window_seconds=window, max_runs=max_runs, state_dir=state_dir)


class ThrottleExceededError(Exception):
    pass


class Throttle:
    def __init__(self, config: ThrottleConfig, job_name: str) -> None:
        self.config = config
        self.job_name = job_name
        self._state_path = Path(config.state_dir) / f"{job_name}.json"

    def _load_timestamps(self) -> list:
        if not self._state_path.exists():
            return []
        try:
            with open(self._state_path) as f:
                return json.load(f).get("runs", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save_timestamps(self, timestamps: list) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._state_path, "w") as f:
            json.dump({"runs": timestamps}, f)

    def _prune(self, timestamps: list) -> list:
        cutoff = time.time() - self.config.window_seconds
        return [t for t in timestamps if t >= cutoff]

    def check(self) -> bool:
        """Return True if the job is allowed to run, False if throttled."""
        if not self.config.enabled:
            return True
        timestamps = self._prune(self._load_timestamps())
        return len(timestamps) < self.config.max_runs

    def record(self) -> None:
        """Record a run timestamp."""
        if not self.config.enabled:
            return
        timestamps = self._prune(self._load_timestamps())
        timestamps.append(time.time())
        self._save_timestamps(timestamps)

    def run_count_in_window(self) -> int:
        if not self.config.enabled:
            return 0
        return len(self._prune(self._load_timestamps()))
