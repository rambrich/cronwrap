"""Integration of retry logic with exponential backoff."""
from __future__ import annotations
from typing import Callable, List
from cronwrap.runner import RunResult
from cronwrap.retry import RetryPolicy
from cronwrap.backoff import BackoffManager, BackoffConfig


def run_with_backoff_retry(
    command: str,
    policy: RetryPolicy,
    backoff: BackoffManager,
    run_fn: Callable[[str], RunResult],
) -> tuple[RunResult, List[float]]:
    """Run command with retry and backoff; return final result and list of delays used."""
    delays_used: List[float] = []
    result = run_fn(command)
    attempt = 0
    while result.returncode != 0 and attempt < policy.max_retries:
        delay = backoff.wait(attempt)
        delays_used.append(delay)
        attempt += 1
        result = run_fn(command)
    return result, delays_used
