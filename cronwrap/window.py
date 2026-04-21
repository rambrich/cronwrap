"""Execution window enforcement — restrict cron jobs to allowed time windows."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional


@dataclass
class WindowConfig:
    enabled: bool = False
    # Comma-separated time ranges like "08:00-18:00,22:00-23:59"
    windows: List[tuple[time, time]] = field(default_factory=list)
    timezone: str = "UTC"

    @staticmethod
    def from_env() -> "WindowConfig":
        enabled = os.environ.get("CRONWRAP_WINDOW_ENABLED", "").lower() == "true"
        raw = os.environ.get("CRONWRAP_WINDOW_RANGES", "").strip()
        tz = os.environ.get("CRONWRAP_WINDOW_TZ", "UTC")
        windows: List[tuple[time, time]] = []
        if enabled and raw:
            for part in raw.split(","):
                part = part.strip()
                if "-" in part:
                    try:
                        start_s, end_s = part.split("-", 1)
                        start = time.fromisoformat(start_s.strip())
                        end = time.fromisoformat(end_s.strip())
                        windows.append((start, end))
                    except ValueError:
                        pass
        return WindowConfig(enabled=enabled, windows=windows, timezone=tz)


class OutsideWindowError(Exception):
    """Raised when a job is attempted outside its allowed execution window."""

    def __init__(self, current: time, windows: List[tuple[time, time]]) -> None:
        self.current = current
        self.windows = windows
        super().__init__(str(self))

    def __str__(self) -> str:  # pragma: no cover
        ranges = ", ".join(f"{s.isoformat()}-{e.isoformat()}" for s, e in self.windows)
        return f"Current time {self.current.isoformat()} is outside allowed windows: [{ranges}]"


class WindowManager:
    def __init__(self, config: WindowConfig) -> None:
        self.config = config

    def _current_time(self) -> time:
        """Return current UTC time (override in tests)."""
        return datetime.utcnow().time().replace(microsecond=0)

    def is_allowed(self, at: Optional[time] = None) -> bool:
        """Return True if *at* (default: now) falls within any configured window."""
        if not self.config.enabled or not self.config.windows:
            return True
        current = at if at is not None else self._current_time()
        for start, end in self.config.windows:
            if start <= end:
                if start <= current <= end:
                    return True
            else:
                # Overnight window e.g. 22:00-06:00
                if current >= start or current <= end:
                    return True
        return False

    def check(self, at: Optional[time] = None) -> None:
        """Raise OutsideWindowError if execution is not currently allowed."""
        if not self.is_allowed(at):
            current = at if at is not None else self._current_time()
            raise OutsideWindowError(current, self.config.windows)
