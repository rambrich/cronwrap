"""Jitter config and manager for randomizing cron job start times."""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class JitterConfig:
    enabled: bool = False
    max_seconds: int = 0
    seed: Optional[int] = None

    @classmethod
    def from_env(cls) -> "JitterConfig":
        enabled = os.environ.get("CRONWRAP_JITTER_ENABLED", "").lower() == "true"
        try:
            max_seconds = int(os.environ.get("CRONWRAP_JITTER_MAX_SECONDS", "0"))
        except ValueError:
            max_seconds = 0
        seed_raw = os.environ.get("CRONWRAP_JITTER_SEED", "")
        seed = int(seed_raw) if seed_raw.isdigit() else None
        return cls(enabled=enabled, max_seconds=max_seconds, seed=seed)


class JitterManager:
    def __init__(self, config: JitterConfig) -> None:
        self.config = config
        self._rng = random.Random(config.seed)

    def delay_seconds(self) -> float:
        """Return a random delay in [0, max_seconds]. Returns 0 when disabled."""
        if not self.config.enabled or self.config.max_seconds <= 0:
            return 0.0
        return self._rng.uniform(0, self.config.max_seconds)

    def apply(self, *, sleep_fn=time.sleep) -> float:
        """Sleep for the jitter duration and return the actual delay applied."""
        delay = self.delay_seconds()
        if delay > 0:
            sleep_fn(delay)
        return delay
