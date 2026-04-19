"""Execution budget: limit total CPU/wall-clock time consumed across runs."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class BudgetConfig:
    enabled: bool = False
    max_seconds_per_day: float = 3600.0
    state_dir: str = "/tmp/cronwrap"

    @staticmethod
    def from_env() -> "BudgetConfig":
        enabled = os.environ.get("CRONWRAP_BUDGET_ENABLED", "").lower() == "true"
        max_sec = float(os.environ.get("CRONWRAP_BUDGET_MAX_SECONDS_PER_DAY", "3600"))
        state_dir = os.environ.get("CRONWRAP_STATE_DIR", "/tmp/cronwrap")
        return BudgetConfig(enabled=enabled, max_seconds_per_day=max_sec, state_dir=state_dir)


class BudgetExceededError(Exception):
    def __init__(self, used: float, limit: float):
        self.used = used
        self.limit = limit
        super().__init__(f"Budget exceeded: {used:.1f}s used of {limit:.1f}s daily limit")


@dataclass
class BudgetState:
    date: str
    total_seconds: float = 0.0


class BudgetManager:
    def __init__(self, config: BudgetConfig, job_name: str = "default"):
        self.config = config
        self.job_name = job_name

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"budget_{self.job_name}.json"

    def _load_state(self) -> BudgetState:
        path = self._state_path()
        today = time.strftime("%Y-%m-%d")
        if path.exists():
            data = json.loads(path.read_text())
            if data.get("date") == today:
                return BudgetState(date=today, total_seconds=data.get("total_seconds", 0.0))
        return BudgetState(date=today)

    def _save_state(self, state: BudgetState) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"date": state.date, "total_seconds": state.total_seconds}))

    def check(self) -> Optional[BudgetExceededError]:
        if not self.config.enabled:
            return None
        state = self._load_state()
        if state.total_seconds >= self.config.max_seconds_per_day:
            return BudgetExceededError(state.total_seconds, self.config.max_seconds_per_day)
        return None

    def record(self, result: RunResult) -> None:
        if not self.config.enabled:
            return
        state = self._load_state()
        state.total_seconds += result.duration
        self._save_state(state)

    def remaining(self) -> float:
        if not self.config.enabled:
            return float("inf")
        state = self._load_state()
        return max(0.0, self.config.max_seconds_per_day - state.total_seconds)
