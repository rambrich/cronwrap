"""Tests for cronwrap.retry_backoff."""
from unittest.mock import MagicMock
from cronwrap.runner import RunResult
from cronwrap.retry import RetryPolicy
from cronwrap.backoff import BackoffConfig, BackoffManager
from cronwrap.retry_backoff import run_with_backoff_retry


def _result(code: int) -> RunResult:
    return RunResult(returncode=code, stdout="", stderr="", duration=0.1, timed_out=False)


def test_success_no_retries_no_delays():
    run_fn = MagicMock(return_value=_result(0))
    policy = RetryPolicy(max_retries=3)
    mgr = BackoffManager(BackoffConfig(enabled=False))
    result, delays = run_with_backoff_retry("echo hi", policy, mgr, run_fn)
    assert result.returncode == 0
    assert delays == []
    assert run_fn.call_count == 1


def test_retries_on_failure_with_delays():
    run_fn = MagicMock(side_effect=[_result(1), _result(1), _result(0)])
    policy = RetryPolicy(max_retries=3)
    slept = []
    cfg = BackoffConfig(enabled=True, base_delay=2.0, multiplier=1.0, max_delay=10.0, jitter=False)
    mgr = BackoffManager(cfg, sleep_fn=slept.append)
    result, delays = run_with_backoff_retry("cmd", policy, mgr, run_fn)
    assert result.returncode == 0
    assert run_fn.call_count == 3
    assert len(delays) == 2
    assert slept == [2.0, 2.0]


def test_exhausted_retries_returns_failure():
    run_fn = MagicMock(return_value=_result(1))
    policy = RetryPolicy(max_retries=2)
    mgr = BackoffManager(BackoffConfig(enabled=False))
    result, delays = run_with_backoff_retry("bad", policy, mgr, run_fn)
    assert result.returncode == 1
    assert run_fn.call_count == 3
