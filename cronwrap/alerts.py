"""Alert thresholds and escalation logic for cronwrap."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class AlertRule:
    max_duration_seconds: Optional[float] = None
    alert_on_failure: bool = True
    alert_on_success: bool = False

    def matches(self, result: RunResult) -> bool:
        if self.alert_on_failure and result.returncode != 0:
            return True
        if self.alert_on_success and result.returncode == 0:
            return True
        if self.max_duration_seconds is not None:
            if result.duration >= self.max_duration_seconds:
                return True
        return False


@dataclass
class AlertConfig:
    enabled: bool = False
    rules: List[AlertRule] = field(default_factory=list)
    webhook_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AlertConfig":
        enabled = os.environ.get("CRONWRAP_ALERTS_ENABLED", "").lower() == "true"
        webhook_url = os.environ.get("CRONWRAP_ALERT_WEBHOOK_URL") or None
        max_dur = os.environ.get("CRONWRAP_ALERT_MAX_DURATION")
        rule = AlertRule(
            max_duration_seconds=float(max_dur) if max_dur else None,
            alert_on_failure=os.environ.get("CRONWRAP_ALERT_ON_FAILURE", "true").lower() == "true",
            alert_on_success=os.environ.get("CRONWRAP_ALERT_ON_SUCCESS", "").lower() == "true",
        )
        return cls(enabled=enabled, rules=[rule], webhook_url=webhook_url)


class AlertManager:
    def __init__(self, config: AlertConfig):
        self.config = config

    def should_alert(self, result: RunResult) -> bool:
        if not self.config.enabled:
            return False
        return any(rule.matches(result) for rule in self.config.rules)

    def build_payload(self, result: RunResult, job_name: str = "cron") -> dict:
        return {
            "job": job_name,
            "returncode": result.returncode,
            "duration": round(result.duration, 3),
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }

    def send(self, result: RunResult, job_name: str = "cron") -> bool:
        """Send webhook alert. Returns True if sent, False otherwise."""
        if not self.should_alert(result):
            return False
        if not self.config.webhook_url:
            return False
        import urllib.request, json
        payload = json.dumps(self.build_payload(result, job_name)).encode()
        req = urllib.request.Request(
            self.config.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
            return True
        except Exception:
            return False
