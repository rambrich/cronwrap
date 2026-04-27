"""Latency tracking and threshold alerting for cron jobs."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class LatencyConfig:
    enabled: bool = False
    warn_seconds: float = 30.0
    crit_seconds: float = 120.0
    state_dir: str = "/tmp/cronwrap/latency"
    window: int = 20

    @classmethod
    def from_env(cls) -> "LatencyConfig":
        enabled = os.environ.get("CRONWRAP_LATENCY_ENABLED", "").lower() == "true"
        warn = float(os.environ.get("CRONWRAP_LATENCY_WARN_SECONDS", "30"))
        crit = float(os.environ.get("CRONWRAP_LATENCY_CRIT_SECONDS", "120"))
        state_dir = os.environ.get("CRONWRAP_LATENCY_STATE_DIR", "/tmp/cronwrap/latency")
        window = int(os.environ.get("CRONWRAP_LATENCY_WINDOW", "20"))
        return cls(enabled=enabled, warn_seconds=warn, crit_seconds=crit,
                   state_dir=state_dir, window=window)


@dataclass
class LatencyResult:
    job: str
    duration: float
    avg_duration: float
    is_warn: bool
    is_crit: bool
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "duration": self.duration,
            "avg_duration": self.avg_duration,
            "is_warn": self.is_warn,
            "is_crit": self.is_crit,
            "sample_count": self.sample_count,
        }


class LatencyManager:
    def __init__(self, config: LatencyConfig, job: str) -> None:
        self.config = config
        self.job = job

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job}.json"

    def _load_samples(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text()).get("samples", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save_samples(self, samples: List[float]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"samples": samples[-self.config.window:]}))

    def record(self, result: RunResult) -> Optional[LatencyResult]:
        if not self.config.enabled:
            return None
        duration = result.duration
        samples = self._load_samples()
        samples.append(duration)
        self._save_samples(samples)
        avg = sum(samples) / len(samples)
        return LatencyResult(
            job=self.job,
            duration=duration,
            avg_duration=round(avg, 4),
            is_warn=duration >= self.config.warn_seconds,
            is_crit=duration >= self.config.crit_seconds,
            sample_count=len(samples),
        )

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
