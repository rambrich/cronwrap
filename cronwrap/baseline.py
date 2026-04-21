"""Baseline performance tracking for cron jobs.

Records historical duration/exit-code statistics so that future runs
can be compared against an established baseline.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class BaselineConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/baseline"
    min_samples: int = 5
    deviation_factor: float = 2.0  # flag if duration > factor * avg

    @classmethod
    def from_env(cls) -> "BaselineConfig":
        enabled = os.environ.get("CRONWRAP_BASELINE_ENABLED", "").lower() in ("1", "true")
        state_dir = os.environ.get("CRONWRAP_BASELINE_DIR", "/tmp/cronwrap/baseline")
        try:
            min_samples = int(os.environ.get("CRONWRAP_BASELINE_MIN_SAMPLES", "5"))
        except ValueError:
            min_samples = 5
        try:
            deviation_factor = float(os.environ.get("CRONWRAP_BASELINE_DEVIATION_FACTOR", "2.0"))
        except ValueError:
            deviation_factor = 2.0
        return cls(enabled=enabled, state_dir=state_dir,
                   min_samples=min_samples, deviation_factor=deviation_factor)


@dataclass
class BaselineViolation:
    command: str
    avg_duration: float
    actual_duration: float
    factor: float

    def __str__(self) -> str:
        return (
            f"Baseline violation for '{self.command}': "
            f"duration {self.actual_duration:.1f}s is {self.factor:.1f}x "
            f"the average {self.avg_duration:.1f}s"
        )


class BaselineManager:
    def __init__(self, config: BaselineConfig) -> None:
        self.config = config

    def _state_path(self, command: str) -> Path:
        safe = command.replace("/", "_").replace(" ", "_")[:64]
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load_samples(self, command: str) -> List[float]:
        path = self._state_path(command)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text()).get("durations", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save_samples(self, command: str, durations: List[float]) -> None:
        path = self._state_path(command)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"durations": durations[-200:]}))

    def record(self, result: RunResult) -> Optional[BaselineViolation]:
        """Record duration and return a violation if the run is anomalously slow."""
        if not self.config.enabled:
            return None
        durations = self._load_samples(result.command)
        violation: Optional[BaselineViolation] = None
        if len(durations) >= self.config.min_samples:
            avg = sum(durations) / len(durations)
            if avg > 0 and result.duration > avg * self.config.deviation_factor:
                factor = result.duration / avg
                violation = BaselineViolation(
                    command=result.command,
                    avg_duration=avg,
                    actual_duration=result.duration,
                    factor=factor,
                )
        durations.append(result.duration)
        self._save_samples(result.command, durations)
        return violation

    def reset(self, command: str) -> None:
        path = self._state_path(command)
        if path.exists():
            path.unlink()

    def stats(self, command: str) -> dict:
        durations = self._load_samples(command)
        if not durations:
            return {"samples": 0, "avg": None, "min": None, "max": None}
        return {
            "samples": len(durations),
            "avg": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
        }
