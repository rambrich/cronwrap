"""Skew detection: tracks execution time drift from expected schedule."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SkewConfig:
    enabled: bool = False
    expected_interval_seconds: int = 3600
    warn_threshold_seconds: int = 60
    state_dir: str = "/tmp/cronwrap/skew"

    @classmethod
    def from_env(cls) -> "SkewConfig":
        enabled = os.environ.get("CRONWRAP_SKEW_ENABLED", "").lower() == "true"
        interval = int(os.environ.get("CRONWRAP_SKEW_INTERVAL_SECONDS", "3600"))
        warn = int(os.environ.get("CRONWRAP_SKEW_WARN_THRESHOLD_SECONDS", "60"))
        state_dir = os.environ.get("CRONWRAP_SKEW_STATE_DIR", "/tmp/cronwrap/skew")
        return cls(
            enabled=enabled,
            expected_interval_seconds=max(1, interval),
            warn_threshold_seconds=max(0, warn),
            state_dir=state_dir,
        )


@dataclass
class SkewResult:
    skewed: bool
    expected_at: Optional[float]
    actual_at: float
    delta_seconds: float
    message: str

    def to_dict(self) -> dict:
        return {
            "skewed": self.skewed,
            "expected_at": self.expected_at,
            "actual_at": self.actual_at,
            "delta_seconds": self.delta_seconds,
            "message": self.message,
        }


class SkewManager:
    def __init__(self, config: SkewConfig, job: str = "default") -> None:
        self.config = config
        self.job = job

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job}.json"

    def _load_last_run(self) -> Optional[float]:
        p = self._state_path()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
            return float(data.get("last_run", 0)) or None
        except (json.JSONDecodeError, ValueError):
            return None

    def _save_last_run(self, ts: float) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"last_run": ts}))

    def check(self) -> Optional[SkewResult]:
        if not self.config.enabled:
            return None
        now = time.time()
        last = self._load_last_run()
        self._save_last_run(now)
        if last is None:
            return SkewResult(
                skewed=False,
                expected_at=None,
                actual_at=now,
                delta_seconds=0.0,
                message="first run, no skew data",
            )
        expected_at = last + self.config.expected_interval_seconds
        delta = abs(now - expected_at)
        skewed = delta > self.config.warn_threshold_seconds
        msg = (
            f"skew detected: {delta:.1f}s off schedule"
            if skewed
            else f"on schedule (delta={delta:.1f}s)"
        )
        return SkewResult(
            skewed=skewed,
            expected_at=expected_at,
            actual_at=now,
            delta_seconds=round(delta, 3),
            message=msg,
        )
