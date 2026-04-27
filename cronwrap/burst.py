"""Burst detection: flag when run frequency spikes above a threshold."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class BurstConfig:
    enabled: bool = False
    window_seconds: int = 300
    max_runs: int = 5
    state_dir: str = "/tmp/cronwrap/burst"

    @classmethod
    def from_env(cls) -> "BurstConfig":
        enabled = os.environ.get("CRONWRAP_BURST_ENABLED", "").lower() == "true"
        window = int(os.environ.get("CRONWRAP_BURST_WINDOW_SECONDS", "300"))
        max_runs = int(os.environ.get("CRONWRAP_BURST_MAX_RUNS", "5"))
        state_dir = os.environ.get("CRONWRAP_BURST_STATE_DIR", "/tmp/cronwrap/burst")
        return cls(enabled=enabled, window_seconds=window, max_runs=max_runs, state_dir=state_dir)


@dataclass
class BurstResult:
    job: str
    run_count: int
    window_seconds: int
    max_runs: int
    is_burst: bool

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "run_count": self.run_count,
            "window_seconds": self.window_seconds,
            "max_runs": self.max_runs,
            "is_burst": self.is_burst,
        }


@dataclass
class BurstManager:
    config: BurstConfig
    job: str
    _timestamps: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.config.enabled:
            self._load_state()

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job}.json"

    def _load_state(self) -> None:
        p = self._state_path()
        if p.exists():
            data = json.loads(p.read_text())
            self._timestamps = data.get("timestamps", [])

    def _save_state(self) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"timestamps": self._timestamps}))

    def _prune(self, now: float) -> None:
        cutoff = now - self.config.window_seconds
        self._timestamps = [t for t in self._timestamps if t >= cutoff]

    def record(self, now: Optional[float] = None) -> Optional[BurstResult]:
        if not self.config.enabled:
            return None
        now = now or time.time()
        self._prune(now)
        self._timestamps.append(now)
        self._save_state()
        count = len(self._timestamps)
        is_burst = count > self.config.max_runs
        return BurstResult(
            job=self.job,
            run_count=count,
            window_seconds=self.config.window_seconds,
            max_runs=self.config.max_runs,
            is_burst=is_burst,
        )

    def reset(self) -> None:
        self._timestamps = []
        p = self._state_path()
        if p.exists():
            p.unlink()
