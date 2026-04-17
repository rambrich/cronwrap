"""High-level overlap-prevention helper used by the pipeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from cronwrap.lockfile import LockConfig, LockFile, LockAcquireError

logger = logging.getLogger(__name__)


@dataclass
class OverlapPolicy:
    """Determines what happens when a lock cannot be acquired."""
    skip: bool = True   # True = skip silently; False = abort with error

    @classmethod
    def from_env(cls, env: dict) -> "OverlapPolicy":
        skip = env.get("CRONWRAP_LOCK_OVERLAP", "skip").lower() != "abort"
        return cls(skip=skip)


class OverlapGuard:
    """Wraps LockFile with policy-aware behaviour for pipeline use."""

    def __init__(self, lock_config: LockConfig, policy: OverlapPolicy) -> None:
        self._lock = LockFile(lock_config)
        self._policy = policy
        self._held = False

    def enter(self) -> bool:
        """
        Try to acquire the lock.
        Returns True if execution should proceed, False if it should be skipped.
        Raises RuntimeError if policy is abort and lock cannot be acquired.
        """
        if not self._lock.config.enabled:
            return True
        acquired = self._lock.acquire()
        if acquired:
            self._held = True
            return True
        if self._policy.skip:
            logger.warning("Overlap detected — skipping job run (lock: %s)",
                           self._lock.config.lock_path)
            return False
        raise RuntimeError(
            f"Overlap detected and policy is abort (lock: {self._lock.config.lock_path})"
        )

    def exit(self) -> None:
        if self._held:
            self._lock.release()
            self._held = False

    def __enter__(self) -> "OverlapGuard":
        self.enter()
        return self

    def __exit__(self, *_) -> None:
        self.exit()
