"""Forecast module: predicts next run outcome based on recent history."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class ForecastConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/forecast"
    window: int = 10  # number of recent runs to consider

    @staticmethod
    def from_env() -> "ForecastConfig":
        enabled = os.environ.get("CRONWRAP_FORECAST_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_FORECAST_DIR", "/tmp/cronwrap/forecast")
        try:
            window = int(os.environ.get("CRONWRAP_FORECAST_WINDOW", "10"))
        except ValueError:
            window = 10
        return ForecastConfig(enabled=enabled, state_dir=state_dir, window=max(1, window))


@dataclass
class ForecastResult:
    job_id: str
    sample_size: int
    failure_rate: float  # 0.0 – 1.0
    avg_duration: float  # seconds
    predicted_success: bool

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "sample_size": self.sample_size,
            "failure_rate": round(self.failure_rate, 4),
            "avg_duration": round(self.avg_duration, 3),
            "predicted_success": self.predicted_success,
        }


@dataclass
class ForecastManager:
    config: ForecastConfig
    _history: List[dict] = field(default_factory=list, init=False)

    def _state_path(self, job_id: str) -> Path:
        return Path(self.config.state_dir) / f"{job_id}.json"

    def _load(self, job_id: str) -> List[dict]:
        path = self._state_path(job_id)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, job_id: str, entries: List[dict]) -> None:
        path = self._state_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries[-self.config.window:]))

    def record(self, job_id: str, result: RunResult) -> None:
        if not self.config.enabled:
            return
        entries = self._load(job_id)
        entries.append({"success": result.success, "duration": result.duration})
        self._save(job_id, entries)

    def predict(self, job_id: str) -> Optional[ForecastResult]:
        if not self.config.enabled:
            return None
        entries = self._load(job_id)
        if not entries:
            return None
        failures = sum(1 for e in entries if not e["success"])
        failure_rate = failures / len(entries)
        avg_duration = sum(e["duration"] for e in entries) / len(entries)
        return ForecastResult(
            job_id=job_id,
            sample_size=len(entries),
            failure_rate=failure_rate,
            avg_duration=avg_duration,
            predicted_success=failure_rate < 0.5,
        )
