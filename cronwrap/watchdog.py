"""Watchdog module: detects if a job has not run within an expected interval."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class WatchdogConfig:
    enabled: bool = False
    interval_seconds: int = 3600  # expected max gap between runs
    state_dir: str = "/tmp/cronwrap/watchdog"
    job_name: str = "default"

    @staticmethod
    def from_env() -> "WatchdogConfig":
        enabled = os.environ.get("CRONWRAP_WATCHDOG_ENABLED", "false").lower() == "true"
        interval = int(os.environ.get("CRONWRAP_WATCHDOG_INTERVAL", "3600"))
        state_dir = os.environ.get("CRONWRAP_WATCHDOG_STATE_DIR", "/tmp/cronwrap/watchdog")
        job_name = os.environ.get("CRONWRAP_JOB_NAME", "default")
        return WatchdogConfig(
            enabled=enabled,
            interval_seconds=interval,
            state_dir=state_dir,
            job_name=job_name,
        )


@dataclass
class WatchdogState:
    last_run_at: float
    job_name: str

    def to_dict(self) -> dict:
        return {"last_run_at": self.last_run_at, "job_name": self.job_name}

    @staticmethod
    def from_dict(d: dict) -> "WatchdogState":
        return WatchdogState(last_run_at=d["last_run_at"], job_name=d["job_name"])


class WatchdogManager:
    def __init__(self, config: WatchdogConfig) -> None:
        self.config = config

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.config.job_name}.json"

    def _load_state(self) -> Optional[WatchdogState]:
        p = self._state_path()
        if not p.exists():
            return None
        try:
            return WatchdogState.from_dict(json.loads(p.read_text()))
        except Exception:
            return None

    def _save_state(self, state: WatchdogState) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state.to_dict()))

    def record(self, result: RunResult) -> Optional[WatchdogState]:
        """Update the last-run timestamp after a successful run."""
        if not self.config.enabled:
            return None
        if not result.success:
            return None
        state = WatchdogState(last_run_at=time.time(), job_name=self.config.job_name)
        self._save_state(state)
        return state

    def is_overdue(self) -> bool:
        """Return True if the job has not run within the expected interval."""
        if not self.config.enabled:
            return False
        state = self._load_state()
        if state is None:
            return False  # no history yet — not considered overdue
        elapsed = time.time() - state.last_run_at
        return elapsed > self.config.interval_seconds

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
