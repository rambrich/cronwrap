"""Drift detection: tracks how far a cron job's actual run time deviates from its expected schedule."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class DriftConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/drift"
    warn_seconds: float = 60.0
    crit_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "DriftConfig":
        enabled = os.environ.get("CRONWRAP_DRIFT_ENABLED", "").lower() in ("1", "true", "yes")
        state_dir = os.environ.get("CRONWRAP_DRIFT_STATE_DIR", "/tmp/cronwrap/drift")
        try:
            warn_seconds = float(os.environ.get("CRONWRAP_DRIFT_WARN_SECONDS", "60"))
        except ValueError:
            warn_seconds = 60.0
        try:
            crit_seconds = float(os.environ.get("CRONWRAP_DRIFT_CRIT_SECONDS", "300"))
        except ValueError:
            crit_seconds = 300.0
        return cls(enabled=enabled, state_dir=state_dir, warn_seconds=warn_seconds, crit_seconds=crit_seconds)


@dataclass
class DriftResult:
    job: str
    expected_at: float
    actual_at: float
    drift_seconds: float
    is_warning: bool
    is_critical: bool

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "expected_at": self.expected_at,
            "actual_at": self.actual_at,
            "drift_seconds": self.drift_seconds,
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
        }


class DriftManager:
    def __init__(self, config: DriftConfig) -> None:
        self.config = config

    def _state_path(self, job: str) -> Path:
        safe = job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def record_expected(self, job: str, expected_at: Optional[float] = None) -> None:
        """Persist the expected run timestamp for a job."""
        if not self.config.enabled:
            return
        path = self._state_path(job)
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = expected_at if expected_at is not None else time.time()
        path.write_text(json.dumps({"expected_at": ts}))

    def check(self, job: str, actual_at: Optional[float] = None) -> Optional[DriftResult]:
        """Compare actual run time against expected; return DriftResult or None."""
        if not self.config.enabled:
            return None
        path = self._state_path(job)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        expected_at = data["expected_at"]
        now = actual_at if actual_at is not None else time.time()
        drift = abs(now - expected_at)
        return DriftResult(
            job=job,
            expected_at=expected_at,
            actual_at=now,
            drift_seconds=drift,
            is_warning=drift >= self.config.warn_seconds,
            is_critical=drift >= self.config.crit_seconds,
        )

    def reset(self, job: str) -> None:
        path = self._state_path(job)
        if path.exists():
            path.unlink()
