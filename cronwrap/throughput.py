"""Throughput tracking: measures runs-per-window and flags drops."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class ThroughputConfig:
    enabled: bool = False
    window_seconds: int = 3600
    min_runs: int = 1
    state_dir: str = "/tmp/cronwrap/throughput"

    @staticmethod
    def from_env() -> "ThroughputConfig":
        enabled = os.environ.get("CRONWRAP_THROUGHPUT_ENABLED", "").lower() == "true"
        try:
            window = int(os.environ.get("CRONWRAP_THROUGHPUT_WINDOW_SECONDS", "3600"))
        except ValueError:
            window = 3600
        try:
            min_runs = int(os.environ.get("CRONWRAP_THROUGHPUT_MIN_RUNS", "1"))
        except ValueError:
            min_runs = 1
        state_dir = os.environ.get("CRONWRAP_THROUGHPUT_STATE_DIR", "/tmp/cronwrap/throughput")
        return ThroughputConfig(enabled=enabled, window_seconds=window, min_runs=min_runs, state_dir=state_dir)


@dataclass
class ThroughputResult:
    job: str
    runs_in_window: int
    window_seconds: int
    min_runs: int
    below_threshold: bool

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "runs_in_window": self.runs_in_window,
            "window_seconds": self.window_seconds,
            "min_runs": self.min_runs,
            "below_threshold": self.below_threshold,
        }


class ThroughputManager:
    def __init__(self, config: ThroughputConfig, job: str) -> None:
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
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_timestamps(self, timestamps: List[float]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(timestamps))

    def record(self, result: RunResult) -> Optional[ThroughputResult]:
        if not self.config.enabled:
            return None
        now = time.time()
        cutoff = now - self.config.window_seconds
        timestamps = [t for t in self._load_timestamps() if t >= cutoff]
        timestamps.append(now)
        self._save_timestamps(timestamps)
        runs = len(timestamps)
        below = runs < self.config.min_runs
        return ThroughputResult(
            job=self.job,
            runs_in_window=runs,
            window_seconds=self.config.window_seconds,
            min_runs=self.config.min_runs,
            below_threshold=below,
        )
