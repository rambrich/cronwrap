"""Graceful signal handling for cronwrap — catches SIGTERM/SIGINT and records interruption."""

import signal
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)


@dataclass
class SignalHandlerConfig:
    enabled: bool = True
    signals: List[int] = field(default_factory=lambda: [signal.SIGTERM, signal.SIGINT])

    @classmethod
    def from_env(cls) -> "SignalHandlerConfig":
        import os
        enabled = os.environ.get("CRONWRAP_SIGNAL_HANDLER_ENABLED", "true").lower() != "false"
        return cls(enabled=enabled)


class SignalInterrupt(Exception):
    """Raised when a handled signal is received."""

    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(f"Interrupted by signal {signum}")


class SignalManager:
    def __init__(self, config: SignalHandlerConfig):
        self.config = config
        self._original: dict = {}
        self._interrupted: Optional[int] = None
        self._callbacks: List[Callable[[int], None]] = []

    def add_callback(self, cb: Callable[[int], None]) -> None:
        self._callbacks.append(cb)

    @property
    def interrupted(self) -> bool:
        return self._interrupted is not None

    @property
    def signal_received(self) -> Optional[int]:
        return self._interrupted

    def _handle(self, signum: int, frame) -> None:
        logger.warning("cronwrap: received signal %d", signum)
        self._interrupted = signum
        for cb in self._callbacks:
            try:
                cb(signum)
            except Exception:
                pass

    def __enter__(self) -> "SignalManager":
        if not self.config.enabled:
            return self
        for sig in self.config.signals:
            self._original[sig] = signal.getsignal(sig)
            signal.signal(sig, self._handle)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if not self.config.enabled:
            return False
        for sig, handler in self._original.items():
            signal.signal(sig, handler)
        self._original.clear()
        return False
