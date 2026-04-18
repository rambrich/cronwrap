"""Circuit breaker: skip execution if too many recent failures."""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CircuitBreakerConfig:
    enabled: bool = False
    threshold: int = 3        # failures before opening
    window: int = 3600        # seconds to look back
    cooldown: int = 600       # seconds to stay open
    state_dir: str = "/tmp/cronwrap/circuit"

    @classmethod
    def from_env(cls) -> "CircuitBreakerConfig":
        enabled = os.environ.get("CRONWRAP_CIRCUIT_BREAKER", "").lower() == "true"
        return cls(
            enabled=enabled,
            threshold=int(os.environ.get("CRONWRAP_CIRCUIT_THRESHOLD", "3")),
            window=int(os.environ.get("CRONWRAP_CIRCUIT_WINDOW", "3600")),
            cooldown=int(os.environ.get("CRONWRAP_CIRCUIT_COOLDOWN", "600")),
            state_dir=os.environ.get("CRONWRAP_CIRCUIT_STATE_DIR", "/tmp/cronwrap/circuit"),
        )


@dataclass
class CircuitState:
    failures: list = field(default_factory=list)  # timestamps
    opened_at: Optional[float] = None


class CircuitOpenError(Exception):
    def __init__(self, cooldown_remaining: float):
        self.cooldown_remaining = cooldown_remaining
        super().__init__(f"Circuit open; retry in {cooldown_remaining:.0f}s")


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig, job_name: str = "default"):
        self.config = config
        self.job_name = job_name
        self._path = Path(config.state_dir) / f"{job_name}.json"

    def _load(self) -> CircuitState:
        if not self._path.exists():
            return CircuitState()
        try:
            data = json.loads(self._path.read_text())
            return CircuitState(failures=data.get("failures", []), opened_at=data.get("opened_at"))
        except (json.JSONDecodeError, OSError):
            return CircuitState()

    def _save(self, state: CircuitState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"failures": state.failures, "opened_at": state.opened_at}))

    def check(self) -> None:
        """Raise CircuitOpenError if circuit is open."""
        if not self.config.enabled:
            return
        state = self._load()
        now = time.time()
        if state.opened_at is not None:
            remaining = self.config.cooldown - (now - state.opened_at)
            if remaining > 0:
                raise CircuitOpenError(remaining)
            # cooldown passed — reset
            state.opened_at = None
            state.failures = []
            self._save(state)

    def record_failure(self) -> None:
        if not self.config.enabled:
            return
        state = self._load()
        now = time.time()
        cutoff = now - self.config.window
        state.failures = [t for t in state.failures if t > cutoff]
        state.failures.append(now)
        if len(state.failures) >= self.config.threshold:
            state.opened_at = now
        self._save(state)

    def record_success(self) -> None:
        if not self.config.enabled:
            return
        state = self._load()
        state.failures = []
        state.opened_at = None
        self._save(state)
