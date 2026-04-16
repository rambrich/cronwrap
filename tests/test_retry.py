"""Tests for cronwrap.retry module."""
import pytest
from unittest.mock import MagicMock

from cronwrap.runner import RunResult
from cronwrap.retry import RetryPolicy, run_with_retry


def _result(returncode=0, timed_out=False):
    return RunResult(returncode=returncode, stdout="", stderr="", duration=0.1, timed_out=timed_out)


def test_no_retry_on_success():
    fn = MagicMock(return_value=_result(0))
    policy = RetryPolicy(max_attempts=3)
    result = run_with_retry(fn, policy, sleep_fn=lambda _: None)
    assert fn.call_count == 1
    assert result.returncode == 0


def test_retries_on_failure():
    fn = MagicMock(return_value=_result(1))
    policy = RetryPolicy(max_attempts=3)
    result = run_with_retry(fn, policy, sleep_fn=lambda _: None)
    assert fn.call_count == 3
    assert result.returncode == 1


def test_succeeds_on_second_attempt():
    fn = MagicMock(side_effect=[_result(1), _result(0)])
    policy = RetryPolicy(max_attempts=3)
    result = run_with_retry(fn, policy, sleep_fn=lambda _: None)
    assert fn.call_count == 2
    assert result.returncode == 0


def test_delay_called_between_retries():
    fn = MagicMock(return_value=_result(1))
    sleep = MagicMock()
    policy = RetryPolicy(max_attempts=3, delay_seconds=2.0)
    run_with_retry(fn, policy, sleep_fn=sleep)
    assert sleep.call_count == 2
    sleep.assert_called_with(2.0)


def test_backoff_increases_delay():
    fn = MagicMock(return_value=_result(1))
    sleep = MagicMock()
    policy = RetryPolicy(max_attempts=3, delay_seconds=1.0, backoff_factor=2.0)
    run_with_retry(fn, policy, sleep_fn=sleep)
    calls = [c.args[0] for c in sleep.call_args_list]
    assert calls == [1.0, 2.0]


def test_no_retry_on_timeout_when_disabled():
    fn = MagicMock(return_value=_result(1, timed_out=True))
    policy = RetryPolicy(max_attempts=3, retry_on_timeout=False)
    result = run_with_retry(fn, policy, sleep_fn=lambda _: None)
    assert fn.call_count == 1
    assert result.timed_out is True
