"""Pause/resume support for cronwrap jobs.

Allows a job to be paused via a state file so that scheduled runs
are skipped until the job is explicitly resumed.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class PauseConfig:
    enabled: bool = True
    state_dir: str = "/tmp/cronwrap/pause"

    @staticmethod
    def from_env() -> "PauseConfig":
        enabled = os.environ.get("CRONWRAP_PAUSE_ENABLED", "true").lower() != "false"
        state_dir = os.environ.get("CRONWRAP_PAUSE_STATE_DIR", "/tmp/cronwrap/pause")
        return PauseConfig(enabled=enabled, state_dir=state_dir)


@dataclass
class PauseState:
    paused: bool
    reason: str
    paused_at: str

    def to_dict(self) -> dict:
        return {
            "paused": self.paused,
            "reason": self.reason,
            "paused_at": self.paused_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PauseState":
        return PauseState(
            paused=data.get("paused", False),
            reason=data.get("reason", ""),
            paused_at=data.get("paused_at", ""),
        )


class PauseManager:
    def __init__(self, config: PauseConfig, job_name: str) -> None:
        self.config = config
        self.job_name = job_name

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_name}.json"

    def is_paused(self) -> bool:
        if not self.config.enabled:
            return False
        path = self._state_path()
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text())
            return data.get("paused", False)
        except (json.JSONDecodeError, OSError):
            return False

    def pause(self, reason: str = "") -> PauseState:
        state = PauseState(
            paused=True,
            reason=reason,
            paused_at=datetime.now(timezone.utc).isoformat(),
        )
        if self.config.enabled:
            path = self._state_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state.to_dict(), indent=2))
        return state

    def resume(self) -> None:
        path = self._state_path()
        if path.exists():
            path.unlink()

    def status(self) -> Optional[PauseState]:
        path = self._state_path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return PauseState.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None
