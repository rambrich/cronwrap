"""Heartbeat: ping a URL after successful (or any) run."""
from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class HeartbeatConfig:
    enabled: bool = False
    url: str = ""
    on_success: bool = True
    on_failure: bool = False
    timeout: int = 10

    @classmethod
    def from_env(cls) -> "HeartbeatConfig":
        url = os.environ.get("CRONWRAP_HEARTBEAT_URL", "")
        enabled = bool(url)
        on_failure = os.environ.get("CRONWRAP_HEARTBEAT_ON_FAILURE", "false").lower() == "true"
        timeout = int(os.environ.get("CRONWRAP_HEARTBEAT_TIMEOUT", "10"))
        return cls(enabled=enabled, url=url, on_success=True, on_failure=on_failure, timeout=timeout)


@dataclass
class HeartbeatManager:
    config: HeartbeatConfig

    def should_ping(self, result: RunResult) -> bool:
        if not self.config.enabled:
            return False
        if result.success and self.config.on_success:
            return True
        if not result.success and self.config.on_failure:
            return True
        return False

    def ping(self, result: RunResult) -> Optional[int]:
        """Send GET request to heartbeat URL. Returns HTTP status or None."""
        if not self.should_ping(result):
            return None
        url = self.config.url
        if not result.success:
            url = url.rstrip("/") + "/fail"
        try:
            with urllib.request.urlopen(url, timeout=self.config.timeout) as resp:
                return resp.status
        except Exception:
            return None
