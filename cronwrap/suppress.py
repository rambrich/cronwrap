"""Suppress repeated identical failures to reduce alert noise."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class SuppressConfig:
    enabled: bool = False
    window_seconds: int = 3600
    threshold: int = 3
    state_dir: str = "/tmp/cronwrap/suppress"

    @classmethod
    def from_env(cls) -> "SuppressConfig":
        enabled = os.environ.get("CRONWRAP_SUPPRESS_ENABLED", "").lower() == "true"
        window = int(os.environ.get("CRONWRAP_SUPPRESS_WINDOW", "3600"))
        threshold = int(os.environ.get("CRONWRAP_SUPPRESS_THRESHOLD", "3"))
        state_dir = os.environ.get("CRONWRAP_SUPPRESS_STATE_DIR", "/tmp/cronwrap/suppress")
        return cls(enabled=enabled, window_seconds=window, threshold=threshold, state_dir=state_dir)


@dataclass
class SuppressState:
    fingerprint: str
    count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    suppressed: bool = False

    def to_dict(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "suppressed": self.suppressed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SuppressState":
        return cls(**data)


class SuppressManager:
    def __init__(self, config: SuppressConfig):
        self.config = config

    def _state_path(self, fingerprint: str) -> Path:
        safe = fingerprint.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load(self, fingerprint: str) -> Optional[SuppressState]:
        path = self._state_path(fingerprint)
        if not path.exists():
            return None
        try:
            return SuppressState.from_dict(json.loads(path.read_text()))
        except Exception:
            return None

    def _save(self, state: SuppressState) -> None:
        path = self._state_path(state.fingerprint)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state.to_dict()))

    def should_suppress(self, result: RunResult) -> bool:
        """Return True if this failure should be suppressed (not alerted)."""
        if not self.config.enabled or result.success:
            return False
        fp = result.command
        now = time.time()
        state = self._load(fp)
        if state is None or (now - state.first_seen) > self.config.window_seconds:
            state = SuppressState(fingerprint=fp, count=1, first_seen=now, last_seen=now)
            self._save(state)
            return False
        state.count += 1
        state.last_seen = now
        if state.count >= self.config.threshold:
            state.suppressed = True
            self._save(state)
            return True
        self._save(state)
        return False

    def reset(self, fingerprint: str) -> None:
        path = self._state_path(fingerprint)
        if path.exists():
            path.unlink()
