"""Tracks how often a job runs and flags unexpected frequency changes."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class FrequencyConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/frequency"
    window_seconds: int = 3600
    min_runs: int = 1
    max_runs: int = 10

    @classmethod
    def from_env(cls) -> "FrequencyConfig":
        enabled = os.environ.get("CRONWRAP_FREQUENCY_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_FREQUENCY_STATE_DIR", "/tmp/cronwrap/frequency")
        try:
            window_seconds = int(os.environ.get("CRONWRAP_FREQUENCY_WINDOW", "3600"))
        except ValueError:
            window_seconds = 3600
        try:
            min_runs = int(os.environ.get("CRONWRAP_FREQUENCY_MIN_RUNS", "1"))
        except ValueError:
            min_runs = 1
        try:
            max_runs = int(os.environ.get("CRONWRAP_FREQUENCY_MAX_RUNS", "10"))
        except ValueError:
            max_runs = 10
        return cls(
            enabled=enabled,
            state_dir=state_dir,
            window_seconds=window_seconds,
            min_runs=min_runs,
            max_runs=max_runs,
        )


@dataclass
class FrequencyResult:
    job: str
    run_count: int
    window_seconds: int
    too_frequent: bool
    too_infrequent: bool

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "run_count": self.run_count,
            "window_seconds": self.window_seconds,
            "too_frequent": self.too_frequent,
            "too_infrequent": self.too_infrequent,
        }

    @property
    def is_anomalous(self) -> bool:
        return self.too_frequent or self.too_infrequent


class FrequencyManager:
    def __init__(self, config: FrequencyConfig, job: str) -> None:
        self.config = config
        self.job = job

    def _state_path(self) -> Path:
        safe = self.job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load_timestamps(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text())
            return data.get("timestamps", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save_timestamps(self, timestamps: List[float]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"timestamps": timestamps}))

    def record(self, result: RunResult) -> Optional[FrequencyResult]:
        if not self.config.enabled:
            return None
        now = time.time()
        cutoff = now - self.config.window_seconds
        timestamps = [t for t in self._load_timestamps() if t >= cutoff]
        timestamps.append(now)
        self._save_timestamps(timestamps)
        count = len(timestamps)
        return FrequencyResult(
            job=self.job,
            run_count=count,
            window_seconds=self.config.window_seconds,
            too_frequent=count > self.config.max_runs,
            too_infrequent=count < self.config.min_runs,
        )

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
