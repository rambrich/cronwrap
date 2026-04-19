"""Escalation: notify additional recipients after repeated failures."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Optional
from cronwrap.runner import RunResult


@dataclass
class EscalationConfig:
    enabled: bool = False
    threshold: int = 3  # consecutive failures before escalating
    recipients: List[str] = field(default_factory=list)
    state_file: str = "/tmp/cronwrap_escalation.json"

    @classmethod
    def from_env(cls) -> "EscalationConfig":
        enabled = os.environ.get("CRONWRAP_ESCALATION_ENABLED", "").lower() == "true"
        threshold = int(os.environ.get("CRONWRAP_ESCALATION_THRESHOLD", "3"))
        raw = os.environ.get("CRONWRAP_ESCALATION_RECIPIENTS", "")
        recipients = [r.strip() for r in raw.split(",") if r.strip()]
        state_file = os.environ.get("CRONWRAP_ESCALATION_STATE_FILE", "/tmp/cronwrap_escalation.json")
        return cls(enabled=enabled, threshold=threshold, recipients=recipients, state_file=state_file)


import json


class EscalationManager:
    def __init__(self, config: EscalationConfig):
        self.config = config
        self._state: dict = self._load_state()

    def _load_state(self) -> dict:
        if not self.config.enabled:
            return {}
        try:
            with open(self.config.state_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_state(self) -> None:
        with open(self.config.state_file, "w") as f:
            json.dump(self._state, f)

    def record(self, result: RunResult, command: str) -> None:
        if not self.config.enabled:
            return
        key = command[:64]
        if result.success:
            self._state[key] = 0
        else:
            self._state[key] = self._state.get(key, 0) + 1
        self._save_state()

    def should_escalate(self, command: str) -> bool:
        if not self.config.enabled or not self.config.recipients:
            return False
        key = command[:64]
        return self._state.get(key, 0) >= self.config.threshold

    def consecutive_failures(self, command: str) -> int:
        key = command[:64]
        return self._state.get(key, 0)

    def reset(self, command: str) -> None:
        key = command[:64]
        self._state.pop(key, None)
        if self.config.enabled:
            self._save_state()
