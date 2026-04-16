"""Retry policy helpers for cronwrap."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from cronwrap.runner import RunResult


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    delay_seconds: float = 0.0
    backoff_factor: float = 1.0
    retry_on_timeout: bool = True

    def delays(self):
        """Yield delay before each retry (not before first attempt)."""
        delay = self.delay_seconds
        for i in range(self.max_attempts - 1):
            yield delay
            delay *= self.backoff_factor if self.backoff_factor > 0 else 1.0


def run_with_retry(
    fn: Callable[[], RunResult],
    policy: RetryPolicy,
    sleep_fn: Optional[Callable[[float], None]] = None,
) -> RunResult:
    """Run fn according to retry policy, returning the last RunResult."""
    _sleep = sleep_fn if sleep_fn is not None else time.sleep
    result: Optional[RunResult] = None
    delays = list(policy.delays())

    for attempt in range(policy.max_attempts):
        result = fn()
        if result.returncode == 0:
            return result
        if not policy.retry_on_timeout and result.timed_out:
            return result
        if attempt < len(delays):
            _sleep(delays[attempt])

    return result  # type: ignore[return-value]
