"""Replay failed runs from the dead-letter queue."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.deadletter import DeadLetterConfig, DeadLetterManager
from cronwrap.runner import RunResult, run_command


@dataclass
class ReplayConfig:
    enabled: bool = False
    max_replays: int = 3

    @classmethod
    def from_env(cls) -> "ReplayConfig":
        enabled = os.environ.get("CRONWRAP_REPLAY_ENABLED", "").lower() == "true"
        max_replays = int(os.environ.get("CRONWRAP_REPLAY_MAX", "3"))
        return cls(enabled=enabled, max_replays=max_replays)


@dataclass
class ReplayResult:
    replayed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[RunResult] = field(default_factory=list)


class ReplayManager:
    def __init__(self, config: ReplayConfig, dl_config: Optional[DeadLetterConfig] = None):
        self.config = config
        self.dl_manager = DeadLetterManager(dl_config or DeadLetterConfig())

    def replay_all(self) -> ReplayResult:
        result = ReplayResult()
        if not self.config.enabled:
            return result

        entries = self.dl_manager.list()
        for entry in entries[: self.config.max_replays]:
            run = run_command(entry.command)
            result.replayed += 1
            result.results.append(run)
            if run.success:
                result.succeeded += 1
                self.dl_manager.remove(entry.id)
            else:
                result.failed += 1

        result.skipped = max(0, len(entries) - self.config.max_replays)
        return result

    def replay_one(self, entry_id: str) -> Optional[RunResult]:
        if not self.config.enabled:
            return None
        entries = self.dl_manager.list()
        for entry in entries:
            if entry.id == entry_id:
                run = run_command(entry.command)
                if run.success:
                    self.dl_manager.remove(entry.id)
                return run
        return None
