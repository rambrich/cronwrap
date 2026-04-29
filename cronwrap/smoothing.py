"""Exponential moving average smoothing for run duration metrics."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SmoothingConfig:
    enabled: bool = False
    alpha: float = 0.3          # EMA smoothing factor (0 < alpha <= 1)
    state_dir: str = "/tmp/cronwrap/smoothing"

    @classmethod
    def from_env(cls) -> "SmoothingConfig":
        enabled = os.environ.get("CRONWRAP_SMOOTHING_ENABLED", "").lower() == "true"
        raw_alpha = os.environ.get("CRONWRAP_SMOOTHING_ALPHA", "0.3")
        try:
            alpha = float(raw_alpha)
            alpha = max(0.01, min(1.0, alpha))
        except ValueError:
            alpha = 0.3
        state_dir = os.environ.get("CRONWRAP_SMOOTHING_STATE_DIR", "/tmp/cronwrap/smoothing")
        return cls(enabled=enabled, alpha=alpha, state_dir=state_dir)


@dataclass
class SmoothingResult:
    job: str
    raw_duration: float
    smoothed_duration: float
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "raw_duration": self.raw_duration,
            "smoothed_duration": round(self.smoothed_duration, 4),
            "sample_count": self.sample_count,
        }


class SmoothingManager:
    def __init__(self, config: SmoothingConfig) -> None:
        self.config = config

    def _state_path(self, job: str) -> Path:
        safe = job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load(self, job: str) -> dict:
        p = self._state_path(job)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"smoothed": None, "count": 0}

    def _save(self, job: str, state: dict) -> None:
        p = self._state_path(job)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state))

    def update(self, job: str, duration: float) -> Optional[SmoothingResult]:
        if not self.config.enabled:
            return None
        state = self._load(job)
        prev = state["smoothed"]
        count = state["count"]
        if prev is None:
            smoothed = duration
        else:
            smoothed = self.config.alpha * duration + (1 - self.config.alpha) * prev
        count += 1
        self._save(job, {"smoothed": smoothed, "count": count})
        return SmoothingResult(
            job=job,
            raw_duration=duration,
            smoothed_duration=smoothed,
            sample_count=count,
        )

    def current(self, job: str) -> Optional[float]:
        if not self.config.enabled:
            return None
        state = self._load(job)
        return state.get("smoothed")

    def reset(self, job: str) -> None:
        p = self._state_path(job)
        if p.exists():
            p.unlink()
