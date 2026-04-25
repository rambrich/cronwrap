"""Regression detection: flag when a job's success rate drops below a threshold."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class RegressionConfig:
    enabled: bool = False
    window: int = 10          # number of recent runs to consider
    threshold: float = 0.5    # minimum success rate before flagging
    state_dir: str = "/tmp/cronwrap/regression"

    @classmethod
    def from_env(cls) -> "RegressionConfig":
        enabled = os.environ.get("CRONWRAP_REGRESSION_ENABLED", "").lower() == "true"
        window = int(os.environ.get("CRONWRAP_REGRESSION_WINDOW", "10"))
        raw_threshold = os.environ.get("CRONWRAP_REGRESSION_THRESHOLD", "0.5")
        try:
            threshold = float(raw_threshold)
        except ValueError:
            threshold = 0.5
        threshold = max(0.0, min(1.0, threshold))
        state_dir = os.environ.get("CRONWRAP_REGRESSION_STATE_DIR", "/tmp/cronwrap/regression")
        return cls(enabled=enabled, window=window, threshold=threshold, state_dir=state_dir)


@dataclass
class RegressionResult:
    job: str
    success_rate: float
    window: int
    is_regression: bool

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "success_rate": self.success_rate,
            "window": self.window,
            "is_regression": self.is_regression,
        }


class RegressionDetector:
    def __init__(self, config: RegressionConfig) -> None:
        self.config = config

    def _state_path(self, job: str) -> Path:
        safe = job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load_history(self, job: str) -> List[bool]:
        path = self._state_path(job)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_history(self, job: str, history: List[bool]) -> None:
        path = self._state_path(job)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(history))

    def record(self, job: str, result: RunResult) -> Optional[RegressionResult]:
        if not self.config.enabled:
            return None
        history = self._load_history(job)
        history.append(result.returncode == 0)
        history = history[-self.config.window :]
        self._save_history(job, history)
        if len(history) < self.config.window:
            return None
        success_rate = sum(history) / len(history)
        is_regression = success_rate < self.config.threshold
        return RegressionResult(
            job=job,
            success_rate=round(success_rate, 4),
            window=len(history),
            is_regression=is_regression,
        )
