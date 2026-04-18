"""Quota: enforce daily/weekly run limits per job."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path


_PERIODS = {"daily": 86400, "weekly": 604800, "hourly": 3600}


@dataclass
class QuotaConfig:
    enabled: bool = False
    period: str = "daily"
    max_runs: int = 1
    state_dir: str = "/tmp/cronwrap/quota"

    @classmethod
    def from_env(cls) -> "QuotaConfig":
        enabled = os.environ.get("CRONWRAP_QUOTA_ENABLED", "").lower() == "true"
        period = os.environ.get("CRONWRAP_QUOTA_PERIOD", "daily")
        max_runs = int(os.environ.get("CRONWRAP_QUOTA_MAX_RUNS", "1"))
        state_dir = os.environ.get("CRONWRAP_QUOTA_STATE_DIR", "/tmp/cronwrap/quota")
        return cls(enabled=enabled, period=period, max_runs=max_runs, state_dir=state_dir)

    @property
    def window_seconds(self) -> int:
        return _PERIODS.get(self.period, 86400)


class QuotaManager:
    def __init__(self, config: QuotaConfig, job_name: str) -> None:
        self.config = config
        self.job_name = job_name
        self._path = Path(config.state_dir) / f"{job_name}_quota.json"

    def _load(self) -> list:
        if not self._path.exists():
            return []
        try:
            with open(self._path) as f:
                return json.load(f).get("runs", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, runs: list) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({"runs": runs}, f)

    def _active(self, runs: list) -> list:
        cutoff = time.time() - self.config.window_seconds
        return [r for r in runs if r >= cutoff]

    def within_quota(self) -> bool:
        if not self.config.enabled:
            return True
        return len(self._active(self._load())) < self.config.max_runs

    def consume(self) -> bool:
        """Record a run. Returns True if within quota, False if quota exceeded."""
        if not self.config.enabled:
            return True
        active = self._active(self._load())
        if len(active) >= self.config.max_runs:
            return False
        active.append(time.time())
        self._save(active)
        return True

    def remaining(self) -> int:
        if not self.config.enabled:
            return -1
        active = self._active(self._load())
        return max(0, self.config.max_runs - len(active))
