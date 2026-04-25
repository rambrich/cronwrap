"""Percentile tracking for run durations."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class PercentileConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/percentile"
    window: int = 100  # max samples to retain
    p50: bool = True
    p95: bool = True
    p99: bool = True

    @staticmethod
    def from_env() -> "PercentileConfig":
        enabled = os.environ.get("CRONWRAP_PERCENTILE_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_PERCENTILE_STATE_DIR", "/tmp/cronwrap/percentile")
        window = int(os.environ.get("CRONWRAP_PERCENTILE_WINDOW", "100"))
        p50 = os.environ.get("CRONWRAP_PERCENTILE_P50", "true").lower() != "false"
        p95 = os.environ.get("CRONWRAP_PERCENTILE_P95", "true").lower() != "false"
        p99 = os.environ.get("CRONWRAP_PERCENTILE_P99", "true").lower() != "false"
        return PercentileConfig(enabled=enabled, state_dir=state_dir, window=window,
                                p50=p50, p95=p95, p99=p99)


@dataclass
class PercentileResult:
    job: str
    sample_count: int
    p50: Optional[float]
    p95: Optional[float]
    p99: Optional[float]

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "sample_count": self.sample_count,
            "p50": self.p50,
            "p95": self.p95,
            "p99": self.p99,
        }


class PercentileManager:
    def __init__(self, config: PercentileConfig) -> None:
        self.config = config

    def _state_path(self, job: str) -> Path:
        safe = job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load_samples(self, job: str) -> List[float]:
        path = self._state_path(job)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_samples(self, job: str, samples: List[float]) -> None:
        path = self._state_path(job)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(samples))

    def record(self, result: RunResult) -> Optional[PercentileResult]:
        if not self.config.enabled:
            return None
        job = result.command
        samples = self._load_samples(job)
        samples.append(result.duration)
        if len(samples) > self.config.window:
            samples = samples[-self.config.window:]
        self._save_samples(job, samples)
        return self._compute(job, samples)

    def _compute(self, job: str, samples: List[float]) -> PercentileResult:
        sorted_samples = sorted(samples)
        n = len(sorted_samples)

        def pct(p: float) -> Optional[float]:
            if n == 0:
                return None
            idx = int(p / 100.0 * n)
            idx = min(idx, n - 1)
            return round(sorted_samples[idx], 4)

        return PercentileResult(
            job=job,
            sample_count=n,
            p50=pct(50) if self.config.p50 else None,
            p95=pct(95) if self.config.p95 else None,
            p99=pct(99) if self.config.p99 else None,
        )

    def get(self, job: str) -> Optional[PercentileResult]:
        if not self.config.enabled:
            return None
        samples = self._load_samples(job)
        if not samples:
            return None
        return self._compute(job, samples)

    def reset(self, job: str) -> None:
        path = self._state_path(job)
        if path.exists():
            path.unlink()
