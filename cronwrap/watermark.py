"""High-watermark tracking for run duration and exit codes."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class WatermarkConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/watermarks"

    @classmethod
    def from_env(cls) -> "WatermarkConfig":
        enabled = os.environ.get("CRONWRAP_WATERMARK_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_WATERMARK_DIR", "/tmp/cronwrap/watermarks")
        return cls(enabled=enabled, state_dir=state_dir)


@dataclass
class WatermarkState:
    command: str
    max_duration: float = 0.0
    min_duration: float = float("inf")
    max_exit_code: int = 0
    total_runs: int = 0

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "max_duration": self.max_duration,
            "min_duration": self.min_duration if self.total_runs > 0 else 0.0,
            "max_exit_code": self.max_exit_code,
            "total_runs": self.total_runs,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WatermarkState":
        obj = cls(command=d["command"])
        obj.max_duration = d.get("max_duration", 0.0)
        obj.min_duration = d.get("min_duration", float("inf"))
        obj.max_exit_code = d.get("max_exit_code", 0)
        obj.total_runs = d.get("total_runs", 0)
        return obj


class WatermarkManager:
    def __init__(self, config: WatermarkConfig):
        self.config = config

    def _state_path(self, command: str) -> Path:
        safe = command.replace("/", "_").replace(" ", "_")[:64]
        return Path(self.config.state_dir) / f"{safe}.json"

    def load(self, command: str) -> Optional[WatermarkState]:
        if not self.config.enabled:
            return None
        path = self._state_path(command)
        if not path.exists():
            return None
        with open(path) as f:
            return WatermarkState.from_dict(json.load(f))

    def record(self, result: RunResult) -> Optional[WatermarkState]:
        if not self.config.enabled:
            return None
        Path(self.config.state_dir).mkdir(parents=True, exist_ok=True)
        path = self._state_path(result.command)
        state = self.load(result.command) or WatermarkState(command=result.command)
        duration = result.duration if result.duration is not None else 0.0
        state.max_duration = max(state.max_duration, duration)
        state.min_duration = min(state.min_duration, duration)
        state.max_exit_code = max(state.max_exit_code, result.exit_code)
        state.total_runs += 1
        with open(path, "w") as f:
            json.dump(state.to_dict(), f)
        return state
