"""Sampling support: run a cron job only a fraction of the time."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SamplingConfig:
    enabled: bool = False
    rate: float = 1.0          # 0.0 – 1.0; 1.0 means always run
    seed: Optional[int] = None  # optional fixed seed for testing

    @classmethod
    def from_env(cls) -> "SamplingConfig":
        enabled_raw = os.environ.get("CRONWRAP_SAMPLING_ENABLED", "").lower()
        enabled = enabled_raw in ("1", "true", "yes")
        rate_raw = os.environ.get("CRONWRAP_SAMPLING_RATE", "1.0")
        try:
            rate = float(rate_raw)
        except ValueError:
            rate = 1.0
        rate = max(0.0, min(1.0, rate))
        seed_raw = os.environ.get("CRONWRAP_SAMPLING_SEED", "")
        seed: Optional[int] = int(seed_raw) if seed_raw.isdigit() else None
        return cls(enabled=enabled, rate=rate, seed=seed)


@dataclass
class SamplingManager:
    config: SamplingConfig
    _rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.config.seed)

    def should_run(self) -> bool:
        """Return True if the job should execute given the configured rate."""
        if not self.config.enabled:
            return True
        if self.config.rate >= 1.0:
            return True
        if self.config.rate <= 0.0:
            return False
        return self._rng.random() < self.config.rate

    def skipped_message(self) -> str:
        return (
            f"[cronwrap] Job skipped by sampler "
            f"(rate={self.config.rate:.2f})"
        )
