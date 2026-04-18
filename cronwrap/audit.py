"""Audit log: records every cronwrap invocation to a structured JSONL file."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class AuditConfig:
    enabled: bool = False
    log_path: str = "/var/log/cronwrap/audit.jsonl"

    @classmethod
    def from_env(cls) -> "AuditConfig":
        enabled = os.environ.get("CRONWRAP_AUDIT_ENABLED", "").lower() in ("1", "true", "yes")
        log_path = os.environ.get("CRONWRAP_AUDIT_LOG", "/var/log/cronwrap/audit.jsonl")
        return cls(enabled=enabled, log_path=log_path)


@dataclass
class AuditEntry:
    timestamp: str
    command: str
    exit_code: int
    duration: float
    success: bool
    retries: int = 0
    tags: list = field(default_factory=list)
    job_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class AuditLogger:
    def __init__(self, config: AuditConfig) -> None:
        self.config = config

    def record(self, result: RunResult, command: str, retries: int = 0,
               tags: Optional[list] = None, job_id: Optional[str] = None) -> Optional[AuditEntry]:
        if not self.config.enabled:
            return None
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            command=command,
            exit_code=result.exit_code,
            duration=result.duration,
            success=result.success,
            retries=retries,
            tags=tags or [],
            job_id=job_id,
        )
        self._write(entry)
        return entry

    def _write(self, entry: AuditEntry) -> None:
        path = Path(self.config.log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def read_all(self) -> list[AuditEntry]:
        path = Path(self.config.log_path)
        if not path.exists():
            return []
        entries = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entries.append(AuditEntry(**data))
        return entries
