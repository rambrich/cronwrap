"""Cascade failure detection — suppress downstream notifications when a root cause is already firing.

When multiple cron jobs fail simultaneously (e.g. because a shared database is
down), only the *first* failure within a time window is treated as a new alert.
Subsequent failures are recorded but marked as "cascaded" so that notification
channels are not flooded.

Configuration is via environment variables:
  CRONWRAP_CASCADE_ENABLED   - '1' to enable (default: disabled)
  CRONWRAP_CASCADE_WINDOW    - seconds in which subsequent failures are cascaded (default: 300)
  CRONWRAP_CASCADE_STATE_DIR - directory for state files (default: /tmp/cronwrap/cascade)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class CascadeConfig:
    enabled: bool = False
    window_seconds: int = 300
    state_dir: str = "/tmp/cronwrap/cascade"

    @classmethod
    def from_env(cls) -> "CascadeConfig":
        enabled = os.environ.get("CRONWRAP_CASCADE_ENABLED", "0") == "1"
        try:
            window = int(os.environ.get("CRONWRAP_CASCADE_WINDOW", "300"))
            if window <= 0:
                window = 300
        except ValueError:
            window = 300
        state_dir = os.environ.get("CRONWRAP_CASCADE_STATE_DIR", "/tmp/cronwrap/cascade")
        return cls(enabled=enabled, window_seconds=window, state_dir=state_dir)


@dataclass
class CascadeState:
    root_command: str
    triggered_at: float
    cascade_count: int = 0

    def to_dict(self) -> dict:
        return {
            "root_command": self.root_command,
            "triggered_at": self.triggered_at,
            "cascade_count": self.cascade_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CascadeState":
        return cls(
            root_command=data["root_command"],
            triggered_at=data["triggered_at"],
            cascade_count=data.get("cascade_count", 0),
        )


@dataclass
class CascadeResult:
    is_cascade: bool
    root_command: Optional[str] = None
    cascade_count: int = 0


class CascadeManager:
    """Detects whether a failure is a cascade of an earlier root-cause failure."""

    def __init__(self, config: CascadeConfig, job_name: str = "default") -> None:
        self.config = config
        self.job_name = job_name

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_name}.json"

    def _load_state(self) -> Optional[CascadeState]:
        path = self._state_path()
        if not path.exists():
            return None
        try:
            with path.open() as fh:
                return CascadeState.from_dict(json.load(fh))
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _save_state(self, state: CascadeState) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as fh:
            json.dump(state.to_dict(), fh)

    def _clear_state(self) -> None:
        path = self._state_path()
        if path.exists():
            path.unlink()

    def check(self, result: RunResult) -> CascadeResult:
        """Evaluate whether *result* is a cascade failure.

        Returns a :class:`CascadeResult` indicating whether the failure should
        be treated as a cascade.  If the feature is disabled, or the result is
        successful, ``is_cascade`` is always ``False``.
        """
        if not self.config.enabled:
            return CascadeResult(is_cascade=False)

        if result.returncode == 0:
            # Successful run clears any existing cascade window.
            self._clear_state()
            return CascadeResult(is_cascade=False)

        now = time.time()
        state = self._load_state()

        if state is None or (now - state.triggered_at) > self.config.window_seconds:
            # This is the root-cause failure — open a new window.
            new_state = CascadeState(root_command=result.command, triggered_at=now)
            self._save_state(new_state)
            return CascadeResult(is_cascade=False)

        # Within the cascade window — record and suppress.
        state.cascade_count += 1
        self._save_state(state)
        return CascadeResult(
            is_cascade=True,
            root_command=state.root_command,
            cascade_count=state.cascade_count,
        )

    def reset(self) -> None:
        """Manually clear the cascade window."""
        self._clear_state()
