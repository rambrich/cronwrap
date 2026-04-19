"""Cooldown manager: enforces a minimum gap between successive runs."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CooldownConfig:
    enabled: bool = False
    min_gap_seconds: int = 300
    state_dir: str = "/tmp/cronwrap/cooldown"

    @classmethod
    def from_env(cls) -> "CooldownConfig":
        enabled = os.environ.get("CRONWRAP_COOLDOWN_ENABLED", "").lower() in ("1", "true", "yes")
        min_gap = int(os.environ.get("CRONWRAP_COOLDOWN_MIN_GAP_SECONDS", "300"))
        state_dir = os.environ.get("CRONWRAP_COOLDOWN_STATE_DIR", "/tmp/cronwrap/cooldown")
        return cls(enabled=enabled, min_gap_seconds=min_gap, state_dir=state_dir)


class CooldownManager:
    def __init__(self, config: CooldownConfig, job_name: str = "default") -> None:
        self.config = config
        self.job_name = job_name

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_name}.json"

    def _load_last_run(self) -> Optional[float]:
        p = self._state_path()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
            return float(data.get("last_run", 0))
        except (ValueError, KeyError, json.JSONDecodeError):
            return None

    def _save_last_run(self, ts: float) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"last_run": ts}))

    def in_cooldown(self) -> bool:
        """Return True if the job is still within its cooldown window."""
        if not self.config.enabled:
            return False
        last = self._load_last_run()
        if last is None:
            return False
        elapsed = time.time() - last
        return elapsed < self.config.min_gap_seconds

    def seconds_remaining(self) -> float:
        """Return how many seconds remain in the cooldown (0 if not in cooldown)."""
        if not self.config.enabled:
            return 0.0
        last = self._load_last_run()
        if last is None:
            return 0.0
        remaining = self.config.min_gap_seconds - (time.time() - last)
        return max(0.0, remaining)

    def record(self, ts: Optional[float] = None) -> None:
        """Record a run timestamp (defaults to now)."""
        if not self.config.enabled:
            return
        self._save_last_run(ts if ts is not None else time.time())

    def reset(self) -> None:
        """Clear cooldown state."""
        p = self._state_path()
        if p.exists():
            p.unlink()
