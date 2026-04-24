"""Cadence tracker: detects when a job runs more or less frequently than expected."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class CadenceConfig:
    enabled: bool = False
    expected_interval_seconds: float = 3600.0
    tolerance_pct: float = 20.0
    state_dir: str = "/tmp/cronwrap/cadence"
    job_id: str = "default"

    @staticmethod
    def from_env() -> "CadenceConfig":
        enabled = os.environ.get("CRONWRAP_CADENCE_ENABLED", "").lower() == "true"
        interval = float(os.environ.get("CRONWRAP_CADENCE_INTERVAL_SECONDS", "3600"))
        tolerance = float(os.environ.get("CRONWRAP_CADENCE_TOLERANCE_PCT", "20"))
        state_dir = os.environ.get("CRONWRAP_CADENCE_STATE_DIR", "/tmp/cronwrap/cadence")
        job_id = os.environ.get("CRONWRAP_JOB_ID", "default")
        return CadenceConfig(
            enabled=enabled,
            expected_interval_seconds=interval,
            tolerance_pct=tolerance,
            state_dir=state_dir,
            job_id=job_id,
        )


@dataclass
class CadenceResult:
    skipped: bool = False
    last_run_ts: Optional[float] = None
    actual_interval_seconds: Optional[float] = None
    expected_interval_seconds: float = 3600.0
    is_early: bool = False
    is_late: bool = False

    def is_anomalous(self) -> bool:
        return self.is_early or self.is_late


class CadenceManager:
    def __init__(self, config: CadenceConfig) -> None:
        self.config = config

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.config.job_id}.json"

    def _load_last_ts(self) -> Optional[float]:
        p = self._state_path()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
            return float(data.get("last_run_ts", 0)) or None
        except (json.JSONDecodeError, ValueError):
            return None

    def _save_ts(self, ts: float) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"last_run_ts": ts}))

    def check(self, result: RunResult) -> Optional[CadenceResult]:
        if not self.config.enabled:
            return None

        now = time.time()
        last_ts = self._load_last_ts()
        self._save_ts(now)

        if last_ts is None:
            return CadenceResult(
                skipped=True,
                expected_interval_seconds=self.config.expected_interval_seconds,
            )

        actual = now - last_ts
        expected = self.config.expected_interval_seconds
        margin = expected * (self.config.tolerance_pct / 100.0)
        is_early = actual < (expected - margin)
        is_late = actual > (expected + margin)

        return CadenceResult(
            last_run_ts=last_ts,
            actual_interval_seconds=actual,
            expected_interval_seconds=expected,
            is_early=is_early,
            is_late=is_late,
        )

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
