"""Tests for cronwrap.scheduler."""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from cronwrap.scheduler import ScheduleConfig, validate_expression, next_run, seconds_until_next_run


# --- ScheduleConfig ---

def test_schedule_config_disabled_by_default():
    cfg = ScheduleConfig.from_env({})
    assert cfg.enabled is False
    assert cfg.expression is None


def test_schedule_config_from_env():
    cfg = ScheduleConfig.from_env({"CRONWRAP_SCHEDULE": "*/5 * * * *"})
    assert cfg.enabled is True
    assert cfg.expression == "*/5 * * * *"


# --- validate_expression ---

def test_validate_expression_valid_without_croniter():
    with patch("cronwrap.scheduler._CRONITER_AVAILABLE", False):
        assert validate_expression("*/5 * * * *") is True


def test_validate_expression_invalid_without_croniter():
    with patch("cronwrap.scheduler._CRONITER_AVAILABLE", False):
        assert validate_expression("bad expression") is False


def test_validate_expression_with_croniter():
    mock_croniter = MagicMock()
    mock_croniter.is_valid.return_value = True
    with patch("cronwrap.scheduler._CRONITER_AVAILABLE", True), \
         patch("cronwrap.scheduler.croniter", mock_croniter):
        result = validate_expression("0 9 * * 1")
    mock_croniter.is_valid.assert_called_once_with("0 9 * * 1")
    assert result is True


# --- next_run ---

def test_next_run_returns_none_without_croniter():
    with patch("cronwrap.scheduler._CRONITER_AVAILABLE", False):
        assert next_run("*/5 * * * *") is None


def test_next_run_returns_none_on_invalid_expression():
    with patch("cronwrap.scheduler._CRONITER_AVAILABLE", False):
        assert next_run("not valid at all") is None


def test_next_run_with_croniter():
    base = datetime(2024, 1, 1, 12, 0, 0)
    expected = datetime(2024, 1, 1, 12, 5, 0)
    mock_iter_instance = MagicMock()
    mock_iter_instance.get_next.return_value = expected
    mock_croniter = MagicMock(return_value=mock_iter_instance)
    mock_croniter.is_valid.return_value = True
    with patch("cronwrap.scheduler._CRONITER_AVAILABLE", True), \
         patch("cronwrap.scheduler.croniter", mock_croniter):
        result = next_run("*/5 * * * *", base)
    assert result == expected


# --- seconds_until_next_run ---

def test_seconds_until_next_run_none_on_invalid():
    with patch("cronwrap.scheduler._CRONITER_AVAILABLE", False):
        assert seconds_until_next_run("bad") is None


def test_seconds_until_next_run_positive():
    base = datetime(2024, 1, 1, 12, 0, 0)
    future = datetime(2024, 1, 1, 12, 5, 0)
    with patch("cronwrap.scheduler.next_run", return_value=future):
        secs = seconds_until_next_run("*/5 * * * *", base)
    assert secs == pytest.approx(300.0)
