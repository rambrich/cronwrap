"""Capacity tracking: monitors resource usage trends over time."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CapacityConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/capacity"
    window: int = 20  # number of samples to keep
    warn_threshold: float = 0.80  # 80% of historical max

    @staticmethod
    def from_env() -> "CapacityConfig":
        enabled = os.environ.get("CRONWRAP_CAPACITY_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_CAPACITY_STATE_DIR", "/tmp/cronwrap/capacity")
        try:
            window = int(os.environ.get("CRONWRAP_CAPACITY_WINDOW", "20"))
            if window < 2:
                window = 2
        except ValueError:
            window = 20
        try:
            warn_threshold = float(os.environ.get("CRONWRAP_CAPACITY_WARN_THRESHOLD", "0.80"))
            warn_threshold = max(0.0, min(1.0, warn_threshold))
        except ValueError:
            warn_threshold = 0.80
        return CapacityConfig(enabled=enabled, state_dir=state_dir, window=window, warn_threshold=warn_threshold)


@dataclass
class CapacityResult:
    job: str
    duration: float
    historical_max: float
    utilization: float  # duration / historical_max
    near_capacity: bool

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "duration": self.duration,
            "historical_max": self.historical_max,
            "utilization": self.utilization,
            "near_capacity": self.near_capacity,
        }


class CapacityManager:
    def __init__(self, config: CapacityConfig, job: str):
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
        p.write_text(json.dumps({"samples": samples, "updated_at": time.time()}))

    def record(self, duration: float) -> Optional[CapacityResult]:
        if not self.config.enabled:
            return None
        samples = self._load_samples()
        samples.append(duration)
        samples = samples[-self.config.window:]
        self._save_samples(samples)
        historical_max = max(samples)
        utilization = duration / historical_max if historical_max > 0 else 0.0
        near_capacity = utilization >= self.config.warn_threshold
        return CapacityResult(
            job=self.job,
            duration=duration,
            historical_max=historical_max,
            utilization=utilization,
            near_capacity=near_capacity,
        )
