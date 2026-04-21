"""Maintenance window support: skip job execution during scheduled maintenance."""
from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class MaintenanceConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap"

    @classmethod
    def from_env(cls) -> "MaintenanceConfig":
        enabled = os.environ.get("CRONWRAP_MAINTENANCE_ENABLED", "").lower() in ("1", "true", "yes")
        state_dir = os.environ.get("CRONWRAP_STATE_DIR", "/tmp/cronwrap")
        return cls(enabled=enabled, state_dir=state_dir)


@dataclass
class MaintenanceWindow:
    start: float
    end: float
    reason: str = ""

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "reason": self.reason}

    @classmethod
    def from_dict(cls, data: dict) -> "MaintenanceWindow":
        return cls(start=data["start"], end=data["end"], reason=data.get("reason", ""))

    def is_active(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        return self.start <= now <= self.end


class MaintenanceManager:
    def __init__(self, config: MaintenanceConfig):
        self.config = config
        Path(config.state_dir).mkdir(parents=True, exist_ok=True)

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / "maintenance.json"

    def _load(self) -> Optional[MaintenanceWindow]:
        p = self._state_path()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
            return MaintenanceWindow.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def is_active(self) -> bool:
        if not self.config.enabled:
            return False
        window = self._load()
        return window is not None and window.is_active()

    def set_window(self, duration_seconds: int, reason: str = "") -> MaintenanceWindow:
        now = time.time()
        window = MaintenanceWindow(start=now, end=now + duration_seconds, reason=reason)
        self._state_path().write_text(json.dumps(window.to_dict()))
        return window

    def clear(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()

    def status(self) -> Optional[MaintenanceWindow]:
        return self._load()
