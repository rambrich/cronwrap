"""Velocity tracking: detects sudden changes in run frequency."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class VelocityConfig:
    enabled: bool = False
    window_seconds: int = 3600
    min_runs: int = 5
    spike_factor: float = 2.0
    state_dir: str = "/tmp/cronwrap/velocity"

    @staticmethod
    def from_env() -> "VelocityConfig":
        enabled = os.environ.get("CRONWRAP_VELOCITY_ENABLED", "false").lower() == "true"
        window = int(os.environ.get("CRONWRAP_VELOCITY_WINDOW", "3600"))
        min_runs = int(os.environ.get("CRONWRAP_VELOCITY_MIN_RUNS", "5"))
        spike_factor = float(os.environ.get("CRONWRAP_VELOCITY_SPIKE_FACTOR", "2.0"))
        state_dir = os.environ.get("CRONWRAP_VELOCITY_STATE_DIR", "/tmp/cronwrap/velocity")
        return VelocityConfig(
            enabled=enabled,
            window_seconds=max(60, window),
            min_runs=max(2, min_runs),
            spike_factor=max(1.1, spike_factor),
            state_dir=state_dir,
        )


@dataclass
class VelocityResult:
    job: str
    run_count: int
    window_seconds: int
    rate_per_hour: float
    baseline_rate: float
    is_spike: bool

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "run_count": self.run_count,
            "window_seconds": self.window_seconds,
            "rate_per_hour": round(self.rate_per_hour, 4),
            "baseline_rate": round(self.baseline_rate, 4),
            "is_spike": self.is_spike,
        }


@dataclass
class VelocityManager:
    config: VelocityConfig
    job: str

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job}.json"

    def _load_timestamps(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except Exception:
            return []

    def _save_timestamps(self, timestamps: List[float]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(timestamps))

    def record(self, result: RunResult) -> Optional[VelocityResult]:
        if not self.config.enabled:
            return None

        now = time.time()
        cutoff = now - self.config.window_seconds
        timestamps = [t for t in self._load_timestamps() if t >= cutoff]
        timestamps.append(now)
        self._save_timestamps(timestamps)

        run_count = len(timestamps)
        rate_per_hour = run_count / (self.config.window_seconds / 3600.0)

        if run_count < self.config.min_runs:
            baseline_rate = rate_per_hour
            is_spike = False
        else:
            older = timestamps[: max(1, run_count // 2)]
            older_span = max(1.0, timestamps[-1] - older[0])
            baseline_rate = len(older) / (older_span / 3600.0)
            is_spike = baseline_rate > 0 and rate_per_hour > baseline_rate * self.config.spike_factor

        return VelocityResult(
            job=self.job,
            run_count=run_count,
            window_seconds=self.config.window_seconds,
            rate_per_hour=rate_per_hour,
            baseline_rate=baseline_rate,
            is_spike=is_spike,
        )

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
