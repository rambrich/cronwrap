"""Cluster-aware run coordination: track which node last ran a job."""
from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class ClusterConfig:
    enabled: bool = False
    state_dir: str = "/tmp/cronwrap/cluster"
    node_id: str = field(default_factory=socket.gethostname)
    stale_seconds: int = 300

    @staticmethod
    def from_env() -> "ClusterConfig":
        enabled = os.environ.get("CRONWRAP_CLUSTER_ENABLED", "").lower() == "true"
        state_dir = os.environ.get("CRONWRAP_CLUSTER_STATE_DIR", "/tmp/cronwrap/cluster")
        node_id = os.environ.get("CRONWRAP_CLUSTER_NODE_ID", socket.gethostname())
        try:
            stale = int(os.environ.get("CRONWRAP_CLUSTER_STALE_SECONDS", "300"))
        except ValueError:
            stale = 300
        return ClusterConfig(enabled=enabled, state_dir=state_dir, node_id=node_id, stale_seconds=stale)


@dataclass
class ClusterState:
    node_id: str
    last_run: float
    success: bool
    command: str

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "last_run": self.last_run,
            "success": self.success,
            "command": self.command,
        }

    @staticmethod
    def from_dict(d: dict) -> "ClusterState":
        return ClusterState(
            node_id=d["node_id"],
            last_run=d["last_run"],
            success=d["success"],
            command=d["command"],
        )


class ClusterManager:
    def __init__(self, config: ClusterConfig) -> None:
        self.config = config

    def _state_path(self, job: str) -> Path:
        safe = job.replace("/", "_").replace(" ", "_")
        return Path(self.config.state_dir) / f"{safe}.json"

    def record(self, job: str, result: RunResult) -> Optional[ClusterState]:
        if not self.config.enabled:
            return None
        state = ClusterState(
            node_id=self.config.node_id,
            last_run=time.time(),
            success=result.exit_code == 0,
            command=result.command,
        )
        path = self._state_path(job)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state.to_dict()))
        return state

    def load(self, job: str) -> Optional[ClusterState]:
        if not self.config.enabled:
            return None
        path = self._state_path(job)
        if not path.exists():
            return None
        try:
            return ClusterState.from_dict(json.loads(path.read_text()))
        except Exception:
            return None

    def is_stale(self, job: str) -> bool:
        state = self.load(job)
        if state is None:
            return True
        age = time.time() - state.last_run
        return age > self.config.stale_seconds
