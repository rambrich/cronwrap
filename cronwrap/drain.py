"""Drain mode: allow in-flight jobs to finish before stopping."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DrainConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/drain"
    timeout_seconds: int = 300

    @classmethod
    def from_env(cls) -> "DrainConfig":
        enabled = os.environ.get("CRONWRAP_DRAIN_ENABLED", "").lower() in ("1", "true", "yes")
        state_dir = os.environ.get("CRONWRAP_DRAIN_STATE_DIR", "/tmp/cronwrap/drain")
        try:
            timeout = int(os.environ.get("CRONWRAP_DRAIN_TIMEOUT", "300"))
        except ValueError:
            timeout = 300
        return cls(enabled=enabled, state_dir=state_dir, timeout_seconds=timeout)


class DrainManager:
    def __init__(self, config: DrainConfig, job_name: str):
        self.config = config
        self.job_name = job_name

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_name}.drain.json"

    def is_draining(self) -> bool:
        if not self.config.enabled:
            return False
        p = self._state_path()
        if not p.exists():
            return False
        try:
            data = json.loads(p.read_text())
            return bool(data.get("draining", False))
        except (json.JSONDecodeError, OSError):
            return False

    def set_draining(self, draining: bool) -> None:
        if not self.config.enabled:
            return
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"draining": draining, "since": time.time()}))

    def wait_until_clear(self, poll_interval: float = 1.0) -> bool:
        """Wait until drain mode is lifted or timeout reached. Returns True if clear."""
        if not self.config.enabled:
            return True
        deadline = time.time() + self.config.timeout_seconds
        while time.time() < deadline:
            if not self.is_draining():
                return True
            time.sleep(poll_interval)
        return False

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
