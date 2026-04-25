"""Saturation detector: tracks resource usage trends and warns when
consecutive run durations suggest the job is approaching a ceiling."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class SaturationConfig:
    enabled: bool = False
    window: int = 10          # number of recent durations to inspect
    threshold: float = 0.90  # fraction of max_duration that triggers a warning
    max_duration: float = 0.0  # seconds; 0 means derive from history max
    state_dir: str = "/tmp/cronwrap/saturation"

    @staticmethod
    def from_env() -> "SaturationConfig":
        enabled = os.environ.get("CRONWRAP_SATURATION_ENABLED", "").lower() == "true"
        window = int(os.environ.get("CRONWRAP_SATURATION_WINDOW", "10"))
        threshold = float(os.environ.get("CRONWRAP_SATURATION_THRESHOLD", "0.90"))
        max_duration = float(os.environ.get("CRONWRAP_SATURATION_MAX_DURATION", "0"))
        state_dir = os.environ.get("CRONWRAP_SATURATION_STATE_DIR", "/tmp/cronwrap/saturation")
        return SaturationConfig(
            enabled=enabled,
            window=max(1, window),
            threshold=min(1.0, max(0.0, threshold)),
            max_duration=max(0.0, max_duration),
            state_dir=state_dir,
        )


@dataclass
class SaturationResult:
    saturated: bool
    ratio: float          # current_avg / ceiling
    avg_duration: float
    ceiling: float
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "saturated": self.saturated,
            "ratio": round(self.ratio, 4),
            "avg_duration": round(self.avg_duration, 3),
            "ceiling": round(self.ceiling, 3),
            "sample_count": self.sample_count,
        }


@dataclass
class SaturationManager:
    config: SaturationConfig
    _history: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.config.enabled:
            Path(self.config.state_dir).mkdir(parents=True, exist_ok=True)
            self._history = self._load()

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / "history.json"

    def _load(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except Exception:
            return []

    def _save(self) -> None:
        self._state_path().write_text(json.dumps(self._history))

    def record(self, result: RunResult) -> Optional[SaturationResult]:
        if not self.config.enabled:
            return None
        self._history.append(result.duration)
        # keep only the most recent window * 3 entries to bound file size
        self._history = self._history[-(self.config.window * 3):]
        self._save()
        return self.check()

    def check(self) -> Optional[SaturationResult]:
        if not self.config.enabled or not self._history:
            return None
        recent = self._history[-self.config.window:]
        avg = sum(recent) / len(recent)
        ceiling = self.config.max_duration if self.config.max_duration > 0 else max(self._history)
        if ceiling == 0:
            return None
        ratio = avg / ceiling
        return SaturationResult(
            saturated=ratio >= self.config.threshold,
            ratio=ratio,
            avg_duration=avg,
            ceiling=ceiling,
            sample_count=len(recent),
        )

    def reset(self) -> None:
        self._history = []
        p = self._state_path()
        if p.exists():
            p.unlink()
