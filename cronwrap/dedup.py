"""Deduplication module: skip runs with identical command+context fingerprints."""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DedupConfig:
    enabled: bool = False
    window_seconds: int = 3600
    state_dir: str = "/tmp/cronwrap/dedup"

    @classmethod
    def from_env(cls) -> "DedupConfig":
        enabled = os.environ.get("CRONWRAP_DEDUP_ENABLED", "").lower() in ("1", "true", "yes")
        window = int(os.environ.get("CRONWRAP_DEDUP_WINDOW", "3600"))
        state_dir = os.environ.get("CRONWRAP_DEDUP_STATE_DIR", "/tmp/cronwrap/dedup")
        return cls(enabled=enabled, window_seconds=window, state_dir=state_dir)


def _fingerprint(command: str, tags: Optional[dict] = None) -> str:
    payload = {"command": command, "tags": tags or {}}
    raw = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


@dataclass
class DedupManager:
    config: DedupConfig = field(default_factory=DedupConfig)

    def _state_path(self, fingerprint: str) -> Path:
        return Path(self.config.state_dir) / f"{fingerprint}.json"

    def is_duplicate(self, command: str, tags: Optional[dict] = None) -> bool:
        """Return True if the same command ran within the dedup window."""
        if not self.config.enabled:
            return False
        fp = _fingerprint(command, tags)
        path = self._state_path(fp)
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text())
            last_run = data.get("last_run", 0)
            return (time.time() - last_run) < self.config.window_seconds
        except (json.JSONDecodeError, OSError):
            return False

    def record(self, command: str, tags: Optional[dict] = None) -> None:
        """Record that command ran now."""
        if not self.config.enabled:
            return
        fp = _fingerprint(command, tags)
        path = self._state_path(fp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fingerprint": fp, "command": command, "last_run": time.time()}))

    def reset(self, command: str, tags: Optional[dict] = None) -> bool:
        """Remove dedup state for a command. Returns True if removed."""
        fp = _fingerprint(command, tags)
        path = self._state_path(fp)
        if path.exists():
            path.unlink()
            return True
        return False
