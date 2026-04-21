"""Environment diff module: detects and reports changes in environment variables between runs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class EnvDiffConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/envdiff"
    tracked_vars: List[str] = field(default_factory=list)

    @staticmethod
    def from_env() -> "EnvDiffConfig":
        enabled = os.environ.get("CRONWRAP_ENVDIFF_ENABLED", "").lower() in ("1", "true")
        state_dir = os.environ.get("CRONWRAP_ENVDIFF_STATE_DIR", "/tmp/cronwrap/envdiff")
        raw = os.environ.get("CRONWRAP_ENVDIFF_VARS", "")
        tracked = [v.strip() for v in raw.split(",") if v.strip()] if raw else []
        return EnvDiffConfig(enabled=enabled, state_dir=state_dir, tracked_vars=tracked)


@dataclass
class EnvDiffResult:
    added: Dict[str, str] = field(default_factory=dict)
    removed: Dict[str, str] = field(default_factory=dict)
    changed: Dict[str, tuple] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": {k: {"before": v[0], "after": v[1]} for k, v in self.changed.items()},
        }


class EnvDiffManager:
    def __init__(self, config: EnvDiffConfig, job_id: str = "default") -> None:
        self.config = config
        self.job_id = job_id

    def _state_path(self) -> Path:
        return Path(self.config.state_dir) / f"{self.job_id}.json"

    def _load_snapshot(self) -> Optional[Dict[str, str]]:
        path = self._state_path()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _save_snapshot(self, snapshot: Dict[str, str]) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot))

    def _capture(self) -> Dict[str, str]:
        if self.config.tracked_vars:
            return {k: os.environ[k] for k in self.config.tracked_vars if k in os.environ}
        return dict(os.environ)

    def diff(self) -> Optional[EnvDiffResult]:
        if not self.config.enabled:
            return None
        current = self._capture()
        previous = self._load_snapshot()
        self._save_snapshot(current)
        if previous is None:
            return EnvDiffResult()
        added = {k: v for k, v in current.items() if k not in previous}
        removed = {k: v for k, v in previous.items() if k not in current}
        changed = {
            k: (previous[k], current[k])
            for k in current
            if k in previous and previous[k] != current[k]
        }
        return EnvDiffResult(added=added, removed=removed, changed=changed)

    def reset(self) -> None:
        path = self._state_path()
        if path.exists():
            path.unlink()
