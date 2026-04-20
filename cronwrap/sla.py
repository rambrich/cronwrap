"""SLA (Service Level Agreement) tracking for cron jobs."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class SLAConfig:
    enabled: bool = False
    max_duration_seconds: float = 0.0
    max_failures_per_day: int = 0
    state_dir: str = "/tmp/cronwrap/sla"
    job_name: str = "default"

    @classmethod
    def from_env(cls) -> "SLAConfig":
        enabled = os.environ.get("CRONWRAP_SLA_ENABLED", "").lower() == "true"
        max_dur = float(os.environ.get("CRONWRAP_SLA_MAX_DURATION", "0"))
        max_fail = int(os.environ.get("CRONWRAP_SLA_MAX_FAILURES_PER_DAY", "0"))
        state_dir = os.environ.get("CRONWRAP_SLA_STATE_DIR", "/tmp/cronwrap/sla")
        job_name = os.environ.get("CRONWRAP_JOB_NAME", "default")
        return cls(
            enabled=enabled,
            max_duration_seconds=max_dur,
            max_failures_per_day=max_fail,
            state_dir=state_dir,
            job_name=job_name,
        )


@dataclass
class SLAViolation:
    job_name: str
    reason: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "reason": self.reason,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
        }


class SLAManager:
    def __init__(self, config: SLAConfig) -> None:
        self.config = config

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.config.job_name}.json"

    def _load_failures_today(self) -> list:
        path = self._state_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            today = time.strftime("%Y-%m-%d")
            return [e for e in data.get("failures", []) if e.get("date") == today]
        except (json.JSONDecodeError, OSError):
            return []

    def _record_failure(self) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(path.read_text()) if path.exists() else {}
        except (json.JSONDecodeError, OSError):
            data = {}
        failures = data.get("failures", [])
        failures.append({"date": time.strftime("%Y-%m-%d"), "ts": time.time()})
        path.write_text(json.dumps({"failures": failures}))

    def check(self, result: RunResult) -> Optional[SLAViolation]:
        if not self.config.enabled:
            return None
        if not result.success:
            self._record_failure()
            if self.config.max_failures_per_day > 0:
                failures = self._load_failures_today()
                if len(failures) > self.config.max_failures_per_day:
                    return SLAViolation(
                        job_name=self.config.job_name,
                        reason="max_failures_per_day exceeded",
                        value=float(len(failures)),
                        threshold=float(self.config.max_failures_per_day),
                    )
        if self.config.max_duration_seconds > 0 and result.duration > self.config.max_duration_seconds:
            return SLAViolation(
                job_name=self.config.job_name,
                reason="max_duration_seconds exceeded",
                value=result.duration,
                threshold=self.config.max_duration_seconds,
            )
        return None
