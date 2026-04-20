"""Execution profiler for cronwrap.

Tracks per-run timing breakdowns (pre-hooks, command, post-hooks, notifications)
and writes a lightweight profile entry to a JSON-lines file for later analysis.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ProfilerConfig:
    enabled: bool = False
    profile_dir: str = "/tmp/cronwrap/profiles"

    @classmethod
    def from_env(cls) -> "ProfilerConfig":
        enabled = os.environ.get("CRONWRAP_PROFILER_ENABLED", "").lower() in ("1", "true", "yes")
        profile_dir = os.environ.get("CRONWRAP_PROFILER_DIR", "/tmp/cronwrap/profiles")
        return cls(enabled=enabled, profile_dir=profile_dir)


@dataclass
class ProfileSpan:
    """A named timing span within a single run."""
    name: str
    start: float = field(default_factory=time.monotonic)
    end: Optional[float] = None

    def stop(self) -> None:
        self.end = time.monotonic()

    @property
    def duration_seconds(self) -> float:
        if self.end is None:
            return time.monotonic() - self.start
        return self.end - self.start

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "duration_seconds": round(self.duration_seconds, 4),
        }


@dataclass
class ProfileEntry:
    """A complete profiling record for one cronwrap execution."""
    command: str
    run_id: str
    timestamp: str
    spans: List[ProfileSpan] = field(default_factory=list)
    total_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "command": self.command,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_seconds": round(self.total_seconds, 4),
            "spans": [s.to_dict() for s in self.spans],
        }


class Profiler:
    """Collects timing spans for a single run and persists the profile."""

    def __init__(self, config: ProfilerConfig, command: str, run_id: str) -> None:
        self.config = config
        self.command = command
        self.run_id = run_id
        self._spans: List[ProfileSpan] = []
        self._run_start: float = time.monotonic()
        self._timestamp: str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def span(self, name: str) -> ProfileSpan:
        """Start a new named span and register it."""
        s = ProfileSpan(name=name)
        self._spans.append(s)
        return s

    def finish(self) -> Optional[ProfileEntry]:
        """Finalise the profile and write it to disk if enabled."""
        if not self.config.enabled:
            return None

        total = time.monotonic() - self._run_start
        entry = ProfileEntry(
            command=self.command,
            run_id=self.run_id,
            timestamp=self._timestamp,
            spans=list(self._spans),
            total_seconds=total,
        )
        self._write(entry)
        return entry

    def _write(self, entry: ProfileEntry) -> None:
        """Append the profile entry as a JSON line."""
        profile_dir = Path(self.config.profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_file = profile_dir / "profiles.jsonl"
        with profile_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def load_all(self) -> List[Dict]:
        """Return all stored profile entries from disk."""
        profile_file = Path(self.config.profile_dir) / "profiles.jsonl"
        if not profile_file.exists():
            return []
        entries: List[Dict] = []
        with profile_file.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries
