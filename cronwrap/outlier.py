"""Outlier detection: flags runs whose duration deviates significantly from the recent mean."""
from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class OutlierConfig:
    enabled: bool = False
    window: int = 20          # number of recent samples to consider
    threshold: float = 2.5    # z-score threshold
    state_dir: str = "/tmp/cronwrap/outlier"

    @staticmethod
    def from_env() -> "OutlierConfig":
        enabled = os.environ.get("CRONWRAP_OUTLIER_ENABLED", "").lower() in ("1", "true", "yes")
        window = int(os.environ.get("CRONWRAP_OUTLIER_WINDOW", "20"))
        try:
            threshold = float(os.environ.get("CRONWRAP_OUTLIER_THRESHOLD", "2.5"))
        except ValueError:
            threshold = 2.5
        state_dir = os.environ.get("CRONWRAP_OUTLIER_STATE_DIR", "/tmp/cronwrap/outlier")
        return OutlierConfig(enabled=enabled, window=window, threshold=threshold, state_dir=state_dir)


@dataclass
class OutlierResult:
    is_outlier: bool
    duration: float
    mean: float
    stddev: float
    z_score: float

    def to_dict(self) -> dict:
        return {
            "is_outlier": self.is_outlier,
            "duration": self.duration,
            "mean": self.mean,
            "stddev": self.stddev,
            "z_score": self.z_score,
        }


class OutlierDetector:
    def __init__(self, config: OutlierConfig, job: str = "default") -> None:
        self.config = config
        self.job = job
        Path(config.state_dir).mkdir(parents=True, exist_ok=True)

    def _state_path(self) -> Path:
        safe = self.job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load_history(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_history(self, history: List[float]) -> None:
        self._state_path().write_text(json.dumps(history[-self.config.window:]))

    def check(self, result: RunResult) -> Optional[OutlierResult]:
        if not self.config.enabled:
            return None
        duration = result.duration
        history = self._load_history()
        history.append(duration)
        self._save_history(history)
        samples = history[-(self.config.window):]
        if len(samples) < 3:
            return None
        mean = statistics.mean(samples)
        stddev = statistics.pstdev(samples)
        if stddev == 0:
            return None
        z_score = abs(duration - mean) / stddev
        is_outlier = z_score >= self.config.threshold
        return OutlierResult(is_outlier=is_outlier, duration=duration, mean=mean, stddev=stddev, z_score=z_score)
