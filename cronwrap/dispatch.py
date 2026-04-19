"""Dispatch hooks: run callbacks on job start, success, failure, or completion."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List
from cronwrap.runner import RunResult


@dataclass
class DispatchConfig:
    enabled: bool = True
    events: List[str] = field(default_factory=lambda: ["success", "failure"])

    @classmethod
    def from_env(cls) -> "DispatchConfig":
        enabled = os.environ.get("CRONWRAP_DISPATCH_ENABLED", "true").lower() != "false"
        raw = os.environ.get("CRONWRAP_DISPATCH_EVENTS", "success,failure")
        events = [e.strip() for e in raw.split(",") if e.strip()]
        return cls(enabled=enabled, events=events)


class DispatchManager:
    def __init__(self, config: DispatchConfig) -> None:
        self.config = config
        self._handlers: Dict[str, List[Callable[[RunResult], None]]] = {
            "start": [],
            "success": [],
            "failure": [],
            "complete": [],
        }

    def on(self, event: str, handler: Callable[[RunResult], None]) -> None:
        """Register a handler for a given event."""
        if event not in self._handlers:
            raise ValueError(f"Unknown event: {event!r}")
        self._handlers[event].append(handler)

    def emit(self, event: str, result: RunResult) -> List[str]:
        """Emit an event, calling all registered handlers. Returns list of fired event names."""
        fired: List[str] = []
        if not self.config.enabled:
            return fired
        if event not in self.config.events and event not in ("start", "complete"):
            return fired
        for handler in self._handlers.get(event, []):
            handler(result)
            fired.append(event)
        return fired

    def emit_for_result(self, result: RunResult) -> List[str]:
        """Emit 'success' or 'failure' based on result, then 'complete'."""
        fired: List[str] = []
        event = "success" if result.exit_code == 0 else "failure"
        fired.extend(self.emit(event, result))
        fired.extend(self.emit("complete", result))
        return fired
