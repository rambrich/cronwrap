"""Flap detection: identifies jobs that rapidly alternate between success and failure."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class FlapConfig:
    enabled: bool = False
    window: int = 5          # number of recent runs to inspect
    threshold: int = 3       # min alternations to consider flapping
    state_dir: str = "/tmp/cronwrap/flap"

    @classmethod
    def from_env(cls) -> "FlapConfig":
        enabled = os.environ.get("CRONWRAP_FLAP_ENABLED", "").lower() in ("1", "true", "yes")
        window = int(os.environ.get("CRONWRAP_FLAP_WINDOW", "5"))
        threshold = int(os.environ.get("CRONWRAP_FLAP_THRESHOLD", "3"))
        state_dir = os.environ.get("CRONWRAP_FLAP_STATE_DIR", "/tmp/cronwrap/flap")
        return cls(enabled=enabled, window=window, threshold=threshold, state_dir=state_dir)


@dataclass
class FlapState:
    job: str
    outcomes: List[bool] = field(default_factory=list)  # True = success
    flapping: bool = False
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "outcomes": self.outcomes,
            "flapping": self.flapping,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FlapState":
        return cls(
            job=d["job"],
            outcomes=d.get("outcomes", []),
            flapping=d.get("flapping", False),
            updated_at=d.get("updated_at", 0.0),
        )


class FlapDetector:
    def __init__(self, config: FlapConfig, job: str) -> None:
        self.config = config
        self.job = job

    def _state_path(self) -> Path:
        safe = self.job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load(self) -> FlapState:
        p = self._state_path()
        if p.exists():
            try:
                return FlapState.from_dict(json.loads(p.read_text()))
            except Exception:
                pass
        return FlapState(job=self.job)

    def _save(self, state: FlapState) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state.to_dict()))

    def _count_alternations(self, outcomes: List[bool]) -> int:
        return sum(1 for i in range(1, len(outcomes)) if outcomes[i] != outcomes[i - 1])

    def record(self, result: RunResult) -> Optional[FlapState]:
        if not self.config.enabled:
            return None
        state = self._load()
        state.outcomes.append(result.exit_code == 0)
        state.outcomes = state.outcomes[-self.config.window:]
        alternations = self._count_alternations(state.outcomes)
        state.flapping = len(state.outcomes) >= 2 and alternations >= self.config.threshold
        state.updated_at = time.time()
        self._save(state)
        return state

    def is_flapping(self) -> bool:
        if not self.config.enabled:
            return False
        return self._load().flapping

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
