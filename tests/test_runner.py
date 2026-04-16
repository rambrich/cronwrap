import pytest
from unittest.mock import patch
from cronwrap.runner import run_command, RunResult


def test_successful_command():
    result = run_command("echo hello")
    assert result.success is True
    assert result.returncode == 0
    assert "hello" in result.stdout
    assert result.attempts == 1


def test_failed_command_no_retries():
    result = run_command("exit 1")
    assert result.success is False
    assert result.returncode == 1
    assert result.attempts == 1


def test_retries_on_failure():
    result = run_command("exit 1", retries=2, retry_delay=0)
    assert result.success is False
    assert result.attempts == 3


def test_succeeds_on_second_attempt(tmp_path):
    flag = tmp_path / "flag"
    # First run creates the flag; second run succeeds because flag exists.
    script = f'test -f {flag} && exit 0; touch {flag}; exit 1'
    result = run_command(script, retries=1, retry_delay=0)
    assert result.success is True
    assert result.attempts == 2


def test_timeout_returns_failure():
    result = run_command("sleep 10", timeout=1)
    assert result.success is False
    assert result.returncode == -1
    assert "timed out" in result.stderr


def test_run_result_fields():
    result = run_command("echo test")
    assert isinstance(result, RunResult)
    assert result.duration > 0
    assert result.command == "echo test"
