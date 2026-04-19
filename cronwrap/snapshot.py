"""Snapshot: capture and compare run output hashes to detect changes."""
from __future__ import annotations
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Optional
from cronwrap.runner import RunResult


@dataclass
class SnapshotConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/snapshots"
    notify_on_change: bool = True

    @classmethod
    def from_env(cls) -> "SnapshotConfig":
        enabled = os.environ.get("CRONWRAP_SNAPSHOT_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_SNAPSHOT_DIR", "/tmp/cronwrap/snapshots")
        notify = os.environ.get("CRONWRAP_SNAPSHOT_NOTIFY_ON_CHANGE", "true").lower() != "false"
        return cls(enabled=enabled, state_dir=state_dir, notify_on_change=notify)


@dataclass
class SnapshotEntry:
    job_name: str
    output_hash: str
    timestamp: str

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "output_hash": self.output_hash, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict) -> "SnapshotEntry":
        return cls(job_name=d["job_name"], output_hash=d["output_hash"], timestamp=d["timestamp"])


class SnapshotManager:
    def __init__(self, config: SnapshotConfig):
        self.config = config

    def _state_path(self, job_name: str) -> str:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return os.path.join(self.config.state_dir, f"{safe}.json")

    def _hash_output(self, result: RunResult) -> str:
        combined = (result.stdout or "") + (result.stderr or "")
        return hashlib.sha256(combined.encode()).hexdigest()

    def load(self, job_name: str) -> Optional[SnapshotEntry]:
        if not self.config.enabled:
            return None
        path = self._state_path(job_name)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return SnapshotEntry.from_dict(json.load(f))

    def record(self, job_name: str, result: RunResult) -> Optional[SnapshotEntry]:
        if not self.config.enabled:
            return None
        import datetime
        os.makedirs(self.config.state_dir, exist_ok=True)
        entry = SnapshotEntry(
            job_name=job_name,
            output_hash=self._hash_output(result),
            timestamp=datetime.datetime.utcnow().isoformat(),
        )
        with open(self._state_path(job_name), "w") as f:
            json.dump(entry.to_dict(), f)
        return entry

    def has_changed(self, job_name: str, result: RunResult) -> bool:
        """Return True if output differs from last snapshot (or no snapshot exists)."""
        if not self.config.enabled:
            return False
        previous = self.load(job_name)
        current_hash = self._hash_output(result)
        if previous is None:
            return True
        return previous.output_hash != current_hash
