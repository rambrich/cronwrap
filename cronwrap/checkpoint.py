"""Checkpoint support: persist and restore run state across invocations."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CheckpointConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/checkpoints"

    @staticmethod
    def from_env() -> "CheckpointConfig":
        enabled = os.environ.get("CRONWRAP_CHECKPOINT_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_CHECKPOINT_DIR", "/tmp/cronwrap/checkpoints")
        return CheckpointConfig(enabled=enabled, state_dir=state_dir)


@dataclass
class CheckpointEntry:
    command: str
    last_success_at: Optional[float]
    last_failure_at: Optional[float]
    consecutive_failures: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "consecutive_failures": self.consecutive_failures,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> "CheckpointEntry":
        return CheckpointEntry(
            command=data["command"],
            last_success_at=data.get("last_success_at"),
            last_failure_at=data.get("last_failure_at"),
            consecutive_failures=data.get("consecutive_failures", 0),
            metadata=data.get("metadata", {}),
        )


class CheckpointManager:
    def __init__(self, config: CheckpointConfig):
        self.config = config

    def _path(self, command: str) -> Path:
        safe = command.replace("/", "_").replace(" ", "_")[:64]
        return Path(self.config.state_dir) / f"{safe}.json"

    def load(self, command: str) -> Optional[CheckpointEntry]:
        if not self.config.enabled:
            return None
        p = self._path(command)
        if not p.exists():
            return None
        try:
            return CheckpointEntry.from_dict(json.loads(p.read_text()))
        except Exception:
            return None

    def save(self, entry: CheckpointEntry) -> None:
        if not self.config.enabled:
            return
        p = self._path(entry.command)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(entry.to_dict(), indent=2))

    def update(self, command: str, success: bool, metadata: Optional[dict] = None) -> Optional[CheckpointEntry]:
        if not self.config.enabled:
            return None
        existing = self.load(command) or CheckpointEntry(command=command, last_success_at=None, last_failure_at=None)
        now = time.time()
        if success:
            existing.last_success_at = now
            existing.consecutive_failures = 0
        else:
            existing.last_failure_at = now
            existing.consecutive_failures += 1
        if metadata:
            existing.metadata.update(metadata)
        self.save(existing)
        return existing
