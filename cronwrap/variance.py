"""Variance tracking: detects when run duration deviates significantly from historical mean."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class VarianceConfig:
    enabled: bool = False
    threshold: float = 2.0  # standard deviations
    min_samples: int = 5
    state_dir: str = "/tmp/cronwrap/variance"

    @classmethod
    def from_env(cls) -> "VarianceConfig":
        enabled = os.environ.get("CRONWRAP_VARIANCE_ENABLED", "").lower() == "true"
        threshold = float(os.environ.get("CRONWRAP_VARIANCE_THRESHOLD", "2.0"))
        min_samples = int(os.environ.get("CRONWRAP_VARIANCE_MIN_SAMPLES", "5"))
        state_dir = os.environ.get("CRONWRAP_VARIANCE_STATE_DIR", "/tmp/cronwrap/variance")
        return cls(enabled=enabled, threshold=threshold, min_samples=min_samples, state_dir=state_dir)


@dataclass
class VarianceResult:
    deviated: bool
    duration: float
    mean: float
    stddev: float
    z_score: float
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "deviated": self.deviated,
            "duration": self.duration,
            "mean": self.mean,
            "stddev": self.stddev,
            "z_score": self.z_score,
            "sample_count": self.sample_count,
        }


class VarianceManager:
    def __init__(self, config: VarianceConfig, job_name: str = "default") -> None:
        self.config = config
        self.job_name = job_name

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_name}.json"

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
        p.write_text(json.dumps({"samples": samples}))

    def check(self, result: RunResult) -> Optional[VarianceResult]:
        if not self.config.enabled:
            return None

        duration = result.duration
        samples = self._load_samples()
        samples.append(duration)
        self._save_samples(samples)

        n = len(samples)
        if n < self.config.min_samples:
            return None

        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        stddev = variance ** 0.5

        if stddev == 0:
            z_score = 0.0
            deviated = False
        else:
            z_score = abs(duration - mean) / stddev
            deviated = z_score > self.config.threshold

        return VarianceResult(
            deviated=deviated,
            duration=duration,
            mean=mean,
            stddev=stddev,
            z_score=z_score,
            sample_count=n,
        )
