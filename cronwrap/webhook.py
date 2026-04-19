"""Webhook notification support for cronwrap."""
from __future__ import annotations
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional
from cronwrap.runner import RunResult


@dataclass
class WebhookConfig:
    enabled: bool = False
    url: str = ""
    on_failure: bool = True
    on_success: bool = False
    timeout: int = 10
    extra_headers: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "WebhookConfig":
        url = os.environ.get("CRONWRAP_WEBHOOK_URL", "")
        enabled = bool(url)
        on_success = os.environ.get("CRONWRAP_WEBHOOK_ON_SUCCESS", "false").lower() == "true"
        on_failure = os.environ.get("CRONWRAP_WEBHOOK_ON_FAILURE", "true").lower() == "true"
        timeout = int(os.environ.get("CRONWRAP_WEBHOOK_TIMEOUT", "10"))
        headers = {}
        raw = os.environ.get("CRONWRAP_WEBHOOK_HEADERS", "")
        for part in raw.split(","):
            part = part.strip()
            if ":" in part:
                k, v = part.split(":", 1)
                headers[k.strip()] = v.strip()
        return cls(enabled=enabled, url=url, on_failure=on_failure,
                   on_success=on_success, timeout=timeout, extra_headers=headers)


@dataclass
class WebhookPayload:
    command: str
    exit_code: int
    success: bool
    duration: float
    stdout: str
    stderr: str

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "success": self.success,
            "duration": self.duration,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


class WebhookManager:
    def __init__(self, config: WebhookConfig):
        self.config = config

    def should_send(self, result: RunResult) -> bool:
        if not self.config.enabled:
            return False
        if result.success and self.config.on_success:
            return True
        if not result.success and self.config.on_failure:
            return True
        return False

    def send(self, result: RunResult) -> Optional[int]:
        if not self.should_send(result):
            return None
        payload = WebhookPayload(
            command=result.command,
            exit_code=result.exit_code,
            success=result.success,
            duration=result.duration,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        data = json.dumps(payload.to_dict()).encode()
        headers = {"Content-Type": "application/json", **self.config.extra_headers}
        req = urllib.request.Request(self.config.url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return resp.status
        except urllib.error.URLError:
            return None
