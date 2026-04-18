"""Exponential backoff configuration and delay calculation."""
from __future__ import annotations
import os
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class BackoffConfig:
    enabled: bool = False
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: bool = True

    @classmethod
    def from_env(cls) -> "BackoffConfig":
        enabled = os.environ.get("CRONWRAP_BACKOFF_ENABLED", "").lower() == "true"
        base_delay = float(os.environ.get("CRONWRAP_BACKOFF_BASE_DELAY", "1.0"))
        max_delay = float(os.environ.get("CRONWRAP_BACKOFF_MAX_DELAY", "60.0"))
        multiplier = float(os.environ.get("CRONWRAP_BACKOFF_MULTIPLIER", "2.0"))
        jitter = os.environ.get("CRONWRAP_BACKOFF_JITTER", "true").lower() != "false"
        return cls(enabled=enabled, base_delay=base_delay, max_delay=max_delay,
                   multiplier=multiplier, jitter=jitter)


def compute_delay(config: BackoffConfig, attempt: int) -> float:
    """Return delay in seconds for the given attempt (0-indexed)."""
    if not config.enabled:
        return 0.0
    delay = min(config.base_delay * (config.multiplier ** attempt), config.max_delay)
    if config.jitter:
        import random
        delay *= (0.5 + random.random() * 0.5)
    return delay


class BackoffManager:
    def __init__(self, config: BackoffConfig, sleep_fn: Callable[[float], None] = time.sleep):
        self.config = config
        self._sleep = sleep_fn

    def wait(self, attempt: int) -> float:
        """Sleep for the computed delay and return the delay used."""
        delay = compute_delay(self.config, attempt)
        if delay > 0:
            self._sleep(delay)
        return delay
