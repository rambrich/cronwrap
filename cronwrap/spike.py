"""Spike detection: flag runs whose duration or exit code deviates sharply from recent history."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class SpikeConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/spike"
    window: int = 20          # number of recent durations to consider
    z_threshold: float = 3.0  # z-score threshold for duration spike
    min_samples: int = 5      # minimum samples before detection is active

    @staticmethod
    def from_env() -> "SpikeConfig":
        enabled = os.environ.get("CRONWRAP_SPIKE_ENABLED", "").lower() in ("1", "true", "yes")
        state_dir = os.environ.get("CRONWRAP_SPIKE_STATE_DIR", "/tmp/cronwrap/spike")
        window = int(os.environ.get("CRONWRAP_SPIKE_WINDOW", "20"))
        z_threshold = float(os.environ.get("CRONWRAP_SPIKE_Z_THRESHOLD", "3.0"))
        min_samples = int(os.environ.get("CRONWRAP_SPIKE_MIN_SAMPLES", "5"))
        return SpikeConfig(
            enabled=enabled,
            state_dir=state_dir,
            window=window,
            z_threshold=z_threshold,
            min_samples=min_samples,
        )


@dataclass
class SpikeResult:
    is_spike: bool
    z_score: Optional[float]
    duration: float
    mean_duration: Optional[float]
    message: str

    def to_dict(self) -> dict:
        return {
            "is_spike": self.is_spike,
            "z_score": self.z_score,
            "duration": self.duration,
            "mean_duration": self.mean_duration,
            "message": self.message,
        }


class SpikeDetector:
    def __init__(self, config: SpikeConfig, job: str = "default") -> None:
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
        self._state_path().write_text(json.dumps(history))

    def check(self, result: RunResult) -> Optional[SpikeResult]:
        if not self.config.enabled:
            return None

        duration = result.duration
        history = self._load_history()
        history.append(duration)
        history = history[-self.config.window:]
        self._save_history(history)

        if len(history) < self.config.min_samples:
            return SpikeResult(
                is_spike=False,
                z_score=None,
                duration=duration,
                mean_duration=None,
                message="insufficient samples for spike detection",
            )

        # Exclude the current sample when computing baseline
        baseline = history[:-1]
        mu = mean(baseline)
        if len(baseline) < 2:
            return SpikeResult(
                is_spike=False,
                z_score=None,
                duration=duration,
                mean_duration=mu,
                message="not enough baseline samples",
            )

        sd = stdev(baseline)
        if sd == 0:
            z = 0.0
        else:
            z = (duration - mu) / sd

        is_spike = abs(z) >= self.config.z_threshold
        msg = f"spike detected (z={z:.2f})" if is_spike else f"normal (z={z:.2f})"
        return SpikeResult(
            is_spike=is_spike,
            z_score=round(z, 4),
            duration=duration,
            mean_duration=round(mu, 4),
            message=msg,
        )

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
