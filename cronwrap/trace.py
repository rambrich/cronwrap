"""Execution tracing — records a structured trace entry for each run."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class TraceConfig:
    enabled: bool = False
    trace_dir: str = "/tmp/cronwrap/traces"

    @staticmethod
    def from_env() -> "TraceConfig":
        enabled = os.environ.get("CRONWRAP_TRACE_ENABLED", "").lower() in ("1", "true")
        trace_dir = os.environ.get("CRONWRAP_TRACE_DIR", "/tmp/cronwrap/traces")
        return TraceConfig(enabled=enabled, trace_dir=trace_dir)


@dataclass
class TraceEntry:
    trace_id: str
    command: str
    started_at: str
    finished_at: str
    exit_code: int
    duration: float
    stdout: str
    stderr: str
    success: bool
    tags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class TraceManager:
    def __init__(self, config: TraceConfig) -> None:
        self.config = config

    def record(self, result: RunResult, command: str, tags: Optional[dict] = None) -> Optional[TraceEntry]:
        if not self.config.enabled:
            return None
        Path(self.config.trace_dir).mkdir(parents=True, exist_ok=True)
        entry = TraceEntry(
            trace_id=str(uuid.uuid4()),
            command=command,
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            exit_code=result.exit_code,
            duration=result.duration,
            stdout=result.stdout,
            stderr=result.stderr,
            success=result.success,
            tags=tags or {},
        )
        path = Path(self.config.trace_dir) / f"{entry.trace_id}.json"
        path.write_text(json.dumps(entry.to_dict(), indent=2))
        return entry

    def load(self, trace_id: str) -> Optional[dict]:
        path = Path(self.config.trace_dir) / f"{trace_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_traces(self) -> list[dict]:
        d = Path(self.config.trace_dir)
        if not d.exists():
            return []
        entries = []
        for f in sorted(d.glob("*.json")):
            try:
                entries.append(json.loads(f.read_text()))
            except Exception:
                pass
        return entries
