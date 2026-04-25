"""Streak tracking: counts consecutive successes or failures for a job."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class StreakConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/streaks"
    alert_on_failure_streak: int = 3
    alert_on_success_streak: int = 0  # 0 = disabled

    @staticmethod
    def from_env() -> "StreakConfig":
        enabled = os.environ.get("CRONWRAP_STREAK_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_STREAK_STATE_DIR", "/tmp/cronwrap/streaks")
        fail_thresh = int(os.environ.get("CRONWRAP_STREAK_FAILURE_ALERT", "3"))
        succ_thresh = int(os.environ.get("CRONWRAP_STREAK_SUCCESS_ALERT", "0"))
        return StreakConfig(
            enabled=enabled,
            state_dir=state_dir,
            alert_on_failure_streak=fail_thresh,
            alert_on_success_streak=succ_thresh,
        )


@dataclass
class StreakState:
    job: str
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_status: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_status": self.last_status,
        }

    @staticmethod
    def from_dict(data: dict) -> "StreakState":
        return StreakState(
            job=data["job"],
            consecutive_failures=data.get("consecutive_failures", 0),
            consecutive_successes=data.get("consecutive_successes", 0),
            last_status=data.get("last_status"),
        )


@dataclass
class StreakResult:
    state: StreakState
    failure_alert: bool = False
    success_alert: bool = False


class StreakManager:
    def __init__(self, config: StreakConfig, job: str) -> None:
        self.config = config
        self.job = job

    def _state_path(self) -> Path:
        safe = self.job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load_state(self) -> StreakState:
        path = self._state_path()
        if path.exists():
            try:
                return StreakState.from_dict(json.loads(path.read_text()))
            except Exception:
                pass
        return StreakState(job=self.job)

    def _save_state(self, state: StreakState) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state.to_dict(), indent=2))

    def record(self, result: RunResult) -> Optional[StreakResult]:
        if not self.config.enabled:
            return None
        state = self._load_state()
        if result.returncode == 0:
            state.consecutive_successes += 1
            state.consecutive_failures = 0
            state.last_status = "success"
        else:
            state.consecutive_failures += 1
            state.consecutive_successes = 0
            state.last_status = "failure"
        self._save_state(state)
        fail_alert = (
            self.config.alert_on_failure_streak > 0
            and state.consecutive_failures >= self.config.alert_on_failure_streak
        )
        succ_alert = (
            self.config.alert_on_success_streak > 0
            and state.consecutive_successes >= self.config.alert_on_success_streak
        )
        return StreakResult(state=state, failure_alert=fail_alert, success_alert=succ_alert)

    def reset(self) -> None:
        path = self._state_path()
        if path.exists():
            path.unlink()
