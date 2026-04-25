"""Heatmap: track run frequency by hour-of-day and day-of-week."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from cronwrap.runner import RunResult


@dataclass
class HeatmapConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/heatmap"

    @staticmethod
    def from_env() -> "HeatmapConfig":
        enabled = os.environ.get("CRONWRAP_HEATMAP_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_HEATMAP_STATE_DIR", "/tmp/cronwrap/heatmap")
        return HeatmapConfig(enabled=enabled, state_dir=state_dir)


@dataclass
class HeatmapState:
    job: str
    # counts[day_of_week][hour] — day 0=Monday, hour 0-23
    counts: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"job": self.job, "counts": self.counts}

    @staticmethod
    def from_dict(d: dict) -> "HeatmapState":
        return HeatmapState(job=d["job"], counts=d.get("counts", {}))

    def record(self, ts: datetime) -> None:
        day = str(ts.weekday())   # 0–6
        hour = str(ts.hour)       # 0–23
        self.counts.setdefault(day, {})
        self.counts[day][hour] = self.counts[day].get(hour, 0) + 1

    def hottest_slot(self) -> Optional[tuple]:
        """Return (day, hour) with the highest run count, or None."""
        best = None
        best_count = 0
        for day, hours in self.counts.items():
            for hour, cnt in hours.items():
                if cnt > best_count:
                    best_count = cnt
                    best = (int(day), int(hour))
        return best


class HeatmapManager:
    def __init__(self, config: HeatmapConfig, job: str) -> None:
        self.config = config
        self.job = job

    def _state_path(self) -> Path:
        safe = self.job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load(self) -> HeatmapState:
        p = self._state_path()
        if p.exists():
            try:
                return HeatmapState.from_dict(json.loads(p.read_text()))
            except Exception:
                pass
        return HeatmapState(job=self.job)

    def _save(self, state: HeatmapState) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state.to_dict(), indent=2))

    def record(self, result: RunResult, ts: Optional[datetime] = None) -> Optional[HeatmapState]:
        if not self.config.enabled:
            return None
        ts = ts or datetime.utcnow()
        state = self._load()
        state.record(ts)
        self._save(state)
        return state

    def load(self) -> Optional[HeatmapState]:
        if not self.config.enabled:
            return None
        return self._load()
