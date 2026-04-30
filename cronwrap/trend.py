"""Trend analysis: tracks success/failure rates over a rolling window."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class TrendConfig:
    enabled: bool = False
    window: int = 20          # number of recent runs to consider
    state_dir: str = "/tmp/cronwrap/trend"

    @staticmethod
    def from_env() -> "TrendConfig":
        enabled = os.environ.get("CRONWRAP_TREND_ENABLED", "").lower() == "true"
        window = int(os.environ.get("CRONWRAP_TREND_WINDOW", "20"))
        if window < 2:
            window = 2
        state_dir = os.environ.get("CRONWRAP_TREND_STATE_DIR", "/tmp/cronwrap/trend")
        return TrendConfig(enabled=enabled, window=window, state_dir=state_dir)


@dataclass
class TrendResult:
    job: str
    success_rate: float          # 0.0 – 1.0
    total_runs: int
    window: int
    is_degrading: bool           # rate dropped below 50 %
    is_recovering: bool          # rate rose above 80 % after being low

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "success_rate": round(self.success_rate, 4),
            "total_runs": self.total_runs,
            "window": self.window,
            "is_degrading": self.is_degrading,
            "is_recovering": self.is_recovering,
        }


@dataclass
class TrendManager:
    config: TrendConfig
    _history: List[int] = field(default_factory=list)  # 1=success, 0=failure

    def _state_path(self, job: str) -> Path:
        return Path(self.config.state_dir) / f"{job}.json"

    def _load(self, job: str) -> List[int]:
        p = self._state_path(job)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self, job: str, history: List[int]) -> None:
        p = self._state_path(job)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(history))

    def record(self, job: str, result: RunResult) -> Optional[TrendResult]:
        if not self.config.enabled:
            return None
        history = self._load(job)
        history.append(1 if result.returncode == 0 else 0)
        # keep only last window * 2 entries to bound file size
        history = history[-(self.config.window * 2):]
        self._save(job, history)
        window_slice = history[-self.config.window:]
        rate = sum(window_slice) / len(window_slice) if window_slice else 1.0
        prev_slice = history[-(self.config.window * 2):-self.config.window]
        prev_rate = sum(prev_slice) / len(prev_slice) if prev_slice else rate
        is_degrading = rate < 0.5
        is_recovering = (prev_rate < 0.5) and (rate >= 0.8)
        return TrendResult(
            job=job,
            success_rate=rate,
            total_runs=len(history),
            window=len(window_slice),
            is_degrading=is_degrading,
            is_recovering=is_recovering,
        )

    def reset(self, job: str) -> None:
        p = self._state_path(job)
        if p.exists():
            p.unlink()
