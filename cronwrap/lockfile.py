"""Lockfile support to prevent overlapping cron job executions."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LockConfig:
    enabled: bool = False
    lock_dir: str = "/tmp"
    job_name: str = "cronwrap"
    timeout: int = 0  # 0 = fail immediately if locked

    @classmethod
    def from_env(cls, env: dict) -> "LockConfig":
        enabled = env.get("CRONWRAP_LOCK", "").lower() in ("1", "true", "yes")
        return cls(
            enabled=enabled,
            lock_dir=env.get("CRONWRAP_LOCK_DIR", "/tmp"),
            job_name=env.get("CRONWRAP_JOB_NAME", "cronwrap"),
            timeout=int(env.get("CRONWRAP_LOCK_TIMEOUT", "0")),
        )

    @property
    def lock_path(self) -> Path:
        return Path(self.lock_dir) / f"{self.job_name}.lock"


class LockAcquireError(RuntimeError):
    """Raised when the lockfile cannot be acquired."""


class LockFile:
    def __init__(self, config: LockConfig) -> None:
        self.config = config
        self._acquired = False

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True on success."""
        if not self.config.enabled:
            return True
        deadline = time.monotonic() + self.config.timeout
        while True:
            try:
                fd = os.open(str(self.config.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                self._acquired = True
                return True
            except FileExistsError:
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.1)

    def release(self) -> None:
        if self._acquired and self.config.enabled:
            try:
                self.config.lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._acquired = False

    def __enter__(self) -> "LockFile":
        if not self.acquire():
            raise LockAcquireError(f"Could not acquire lock: {self.config.lock_path}")
        return self

    def __exit__(self, *_) -> None:
        self.release()
