"""Rate limiting to prevent alert/notification storms."""
from __future__ import annotations
import os
import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RateLimitConfig:
    enabled: bool = False
    window_seconds: int = 3600
    max_events: int = 5
    state_file: str = "/tmp/cronwrap_ratelimit.json"

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        enabled = os.environ.get("CRONWRAP_RATELIMIT_ENABLED", "").lower() == "true"
        return cls(
            enabled=enabled,
            window_seconds=int(os.environ.get("CRONWRAP_RATELIMIT_WINDOW", 3600)),
            max_events=int(os.environ.get("CRONWRAP_RATELIMIT_MAX_EVENTS", 5)),
            state_file=os.environ.get("CRONWRAP_RATELIMIT_STATE_FILE", "/tmp/cronwrap_ratelimit.json"),
        )


class RateLimiter:
    def __init__(self, config: RateLimitConfig, job_name: str = "default"):
        self.config = config
        self.job_name = job_name

    def _load_state(self) -> dict:
        path = Path(self.config.state_file)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_state(self, state: dict) -> None:
        Path(self.config.state_file).write_text(json.dumps(state))

    def is_allowed(self) -> bool:
        if not self.config.enabled:
            return True
        now = time.time()
        state = self._load_state()
        events = state.get(self.job_name, [])
        cutoff = now - self.config.window_seconds
        events = [t for t in events if t > cutoff]
        if len(events) >= self.config.max_events:
            return False
        events.append(now)
        state[self.job_name] = events
        self._save_state(state)
        return True

    def remaining(self) -> int:
        if not self.config.enabled:
            return self.config.max_events
        now = time.time()
        state = self._load_state()
        events = state.get(self.job_name, [])
        cutoff = now - self.config.window_seconds
        events = [t for t in events if t > cutoff]
        return max(0, self.config.max_events - len(events))
