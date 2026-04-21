"""Trendline analysis: detect improving/degrading run duration trends."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class TrendlineConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap"
    window: int = 10  # number of recent runs to consider
    threshold: float = 0.20  # 20% change triggers a trend alert

    @staticmethod
    def from_env() -> "TrendlineConfig":
        enabled = os.environ.get("CRONWRAP_TRENDLINE_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_STATE_DIR", "/tmp/cronwrap")
        try:
            window = int(os.environ.get("CRONWRAP_TRENDLINE_WINDOW", "10"))
        except ValueError:
            window = 10
        try:
            threshold = float(os.environ.get("CRONWRAP_TRENDLINE_THRESHOLD", "0.20"))
        except ValueError:
            threshold = 0.20
        return TrendlineConfig(enabled=enabled, state_dir=state_dir, window=window, threshold=threshold)


@dataclass
class TrendResult:
    direction: str  # "improving", "degrading", "stable", "insufficient_data"
    average_before: Optional[float]
    average_after: Optional[float]
    change_pct: Optional[float]

    def is_degrading(self) -> bool:
        return self.direction == "degrading"

    def is_improving(self) -> bool:
        return self.direction == "improving"


class TrendlineManager:
    def __init__(self, config: TrendlineConfig, job_name: str = "default"):
        self.config = config
        self.job_name = job_name

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"trendline_{self.job_name}.json"

    def _load_durations(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_durations(self, durations: List[float]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(durations))

    def record(self, result: RunResult) -> Optional[TrendResult]:
        if not self.config.enabled:
            return None
        durations = self._load_durations()
        durations.append(result.duration)
        durations = durations[-(self.config.window * 2):]
        self._save_durations(durations)
        return self.analyze(durations)

    def analyze(self, durations: List[float]) -> TrendResult:
        w = self.config.window
        if len(durations) < w + 1:
            return TrendResult("insufficient_data", None, None, None)
        before = durations[-(w * 2):-w]
        after = durations[-w:]
        avg_before = sum(before) / len(before) if before else None
        avg_after = sum(after) / len(after)
        if avg_before is None or avg_before == 0:
            return TrendResult("stable", avg_before, avg_after, None)
        change_pct = (avg_after - avg_before) / avg_before
        if change_pct > self.config.threshold:
            direction = "degrading"
        elif change_pct < -self.config.threshold:
            direction = "improving"
        else:
            direction = "stable"
        return TrendResult(direction, avg_before, avg_after, change_pct)
