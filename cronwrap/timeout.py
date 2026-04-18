"""Timeout configuration and enforcement for cron jobs."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TimeoutConfig:
    enabled: bool = False
    seconds: int = 0
    kill_after: int = 5  # grace period before SIGKILL

    @classmethod
    def from_env(cls) -> "TimeoutConfig":
        raw = os.environ.get("CRONWRAP_TIMEOUT", "")
        if not raw:
            return cls(enabled=False)
        try:
            seconds = int(raw)
        except ValueError:
            return cls(enabled=False)
        kill_after = int(os.environ.get("CRONWRAP_TIMEOUT_KILL_AFTER", "5"))
        return cls(enabled=True, seconds=seconds, kill_after=kill_after)


class TimeoutExceededError(Exception):
    def __init__(self, seconds: int):
        self.seconds = seconds
        super().__init__(f"Command timed out after {seconds}s")


class TimeoutManager:
    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()

    def get_timeout(self) -> Optional[int]:
        """Return timeout in seconds, or None if disabled."""
        if not self.config.enabled or self.config.seconds <= 0:
            return None
        return self.config.seconds

    def get_kill_after(self) -> int:
        return self.config.kill_after

    def check_result(self, returncode: int, elapsed: float) -> None:
        """Raise TimeoutExceededError if returncode indicates timeout."""
        if not self.config.enabled:
            return
        # subprocess with timeout raises TimeoutExpired; returncode -9 or -15
        # indicates the process was killed; we check elapsed vs configured
        if self.config.seconds > 0 and elapsed >= self.config.seconds:
            raise TimeoutExceededError(self.config.seconds)
