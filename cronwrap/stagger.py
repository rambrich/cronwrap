"""Stagger: spread cron job starts across a time window to avoid thundering herd."""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class StaggerConfig:
    enabled: bool = False
    window_seconds: int = 60
    seed: Optional[str] = None  # deterministic offset seed (e.g. hostname+job name)

    @staticmethod
    def from_env() -> "StaggerConfig":
        enabled = os.environ.get("CRONWRAP_STAGGER_ENABLED", "").lower() in ("1", "true", "yes")
        try:
            window = int(os.environ.get("CRONWRAP_STAGGER_WINDOW", "60"))
        except ValueError:
            window = 60
        seed = os.environ.get("CRONWRAP_STAGGER_SEED") or None
        return StaggerConfig(enabled=enabled, window_seconds=max(0, window), seed=seed)


def _offset_seconds(window: int, seed: Optional[str]) -> float:
    """Return a deterministic offset in [0, window) based on seed, or random if no seed."""
    if not seed:
        import random
        return random.uniform(0, window)
    digest = hashlib.md5(seed.encode()).hexdigest()  # noqa: S324
    value = int(digest[:8], 16)
    return (value % (window * 1000)) / 1000.0


class StaggerManager:
    def __init__(self, config: StaggerConfig) -> None:
        self.config = config

    def delay_seconds(self) -> float:
        """Return how many seconds to sleep before running the job."""
        if not self.config.enabled or self.config.window_seconds <= 0:
            return 0.0
        return _offset_seconds(self.config.window_seconds, self.config.seed)

    def apply(self) -> float:
        """Sleep for the computed stagger delay and return the actual delay used."""
        delay = self.delay_seconds()
        if delay > 0:
            time.sleep(delay)
        return delay
