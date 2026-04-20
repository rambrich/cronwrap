"""Anomaly detection for run durations and failure rates."""
from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class AnomalyConfig:
    enabled: bool = False
    state_dir: str = ".cronwrap/anomaly"
    window: int = 20          # number of recent runs to consider
    z_score_threshold: float = 2.5  # standard deviations
    min_samples: int = 5      # minimum samples before detection fires

    @staticmethod
    def from_env() -> "AnomalyConfig":
        enabled = os.environ.get("CRONWRAP_ANOMALY_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_ANOMALY_STATE_DIR", ".cronwrap/anomaly")
        window = int(os.environ.get("CRONWRAP_ANOMALY_WINDOW", "20"))
        threshold = float(os.environ.get("CRONWRAP_ANOMALY_Z_SCORE", "2.5"))
        min_samples = int(os.environ.get("CRONWRAP_ANOMALY_MIN_SAMPLES", "5"))
        return AnomalyConfig(
            enabled=enabled,
            state_dir=state_dir,
            window=window,
            z_score_threshold=threshold,
            min_samples=min_samples,
        )


@dataclass
class AnomalyResult:
    is_anomaly: bool
    z_score: Optional[float]
    mean: Optional[float]
    stddev: Optional[float]
    duration: float
    reason: str = ""


class AnomalyDetector:
    def __init__(self, config: AnomalyConfig, job_id: str = "default") -> None:
        self.config = config
        self.job_id = job_id

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_id}.json"

    def _load_history(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_history(self, history: List[float]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(history[-self.config.window :]))

    def check(self, result: RunResult) -> Optional[AnomalyResult]:
        if not self.config.enabled:
            return None

        duration = result.duration
        history = self._load_history()
        history.append(duration)
        self._save_history(history)

        window = history[-(self.config.window + 1) : -1]  # exclude current
        if len(window) < self.config.min_samples:
            return AnomalyResult(
                is_anomaly=False,
                z_score=None,
                mean=None,
                stddev=None,
                duration=duration,
                reason="insufficient samples",
            )

        mean = statistics.mean(window)
        stddev = statistics.pstdev(window)
        if stddev == 0:
            return AnomalyResult(
                is_anomaly=False,
                z_score=0.0,
                mean=mean,
                stddev=stddev,
                duration=duration,
                reason="zero variance",
            )

        z = abs(duration - mean) / stddev
        is_anomaly = z >= self.config.z_score_threshold
        return AnomalyResult(
            is_anomaly=is_anomaly,
            z_score=round(z, 4),
            mean=round(mean, 4),
            stddev=round(stddev, 4),
            duration=duration,
            reason=f"z={z:.2f} >= threshold={self.config.z_score_threshold}" if is_anomaly else "",
        )
