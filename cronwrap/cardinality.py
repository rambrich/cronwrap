"""Cardinality tracking: count unique output patterns over a rolling window."""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class CardinalityConfig:
    enabled: bool = False
    window_seconds: int = 3600
    max_unique: int = 20
    state_dir: str = "/tmp/cronwrap/cardinality"

    @staticmethod
    def from_env() -> "CardinalityConfig":
        enabled = os.environ.get("CRONWRAP_CARDINALITY_ENABLED", "").lower() == "true"
        window = int(os.environ.get("CRONWRAP_CARDINALITY_WINDOW", "3600"))
        max_unique = int(os.environ.get("CRONWRAP_CARDINALITY_MAX_UNIQUE", "20"))
        state_dir = os.environ.get("CRONWRAP_CARDINALITY_STATE_DIR", "/tmp/cronwrap/cardinality")
        return CardinalityConfig(enabled=enabled, window_seconds=window,
                                 max_unique=max_unique, state_dir=state_dir)


@dataclass
class CardinalityResult:
    job: str
    unique_count: int
    exceeded: bool
    max_unique: int

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "unique_count": self.unique_count,
            "exceeded": self.exceeded,
            "max_unique": self.max_unique,
        }


@dataclass
class CardinalityState:
    entries: List[dict] = field(default_factory=list)  # [{"hash": str, "ts": float}]

    def to_dict(self) -> dict:
        return {"entries": self.entries}

    @staticmethod
    def from_dict(d: dict) -> "CardinalityState":
        return CardinalityState(entries=d.get("entries", []))


class CardinalityManager:
    def __init__(self, config: CardinalityConfig, job: str):
        self.config = config
        self.job = job

    def _state_path(self) -> Path:
        safe = self.job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def _load_state(self) -> CardinalityState:
        p = self._state_path()
        if p.exists():
            try:
                return CardinalityState.from_dict(json.loads(p.read_text()))
            except Exception:
                pass
        return CardinalityState()

    def _save_state(self, state: CardinalityState) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state.to_dict()))

    def record(self, result: RunResult) -> Optional[CardinalityResult]:
        if not self.config.enabled:
            return None
        output_hash = hashlib.sha256((result.stdout + result.stderr).encode()).hexdigest()[:16]
        now = time.time()
        cutoff = now - self.config.window_seconds
        state = self._load_state()
        state.entries = [e for e in state.entries if e["ts"] >= cutoff]
        hashes = {e["hash"] for e in state.entries}
        if output_hash not in hashes:
            state.entries.append({"hash": output_hash, "ts": now})
        self._save_state(state)
        unique_count = len({e["hash"] for e in state.entries})
        exceeded = unique_count > self.config.max_unique
        return CardinalityResult(
            job=self.job,
            unique_count=unique_count,
            exceeded=exceeded,
            max_unique=self.config.max_unique,
        )

    def reset(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()
