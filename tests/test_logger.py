import logging
from unittest.mock import MagicMock

import pytest

from cronwrap.logger import LogConfig, log_run_result, setup_logger


def _make_result(success=True, returncode=0, duration=1.0, stdout="", stderr="", timed_out=False):
    r = MagicMock()
    r.success = success
    r.returncode = returncode
    r.duration = duration
    r.stdout = stdout
    r.stderr = stderr
    r.timed_out = timed_out
    return r


def test_setup_logger_returns_logger():
    config = LogConfig(job_name="test_job")
    logger = setup_logger(config)
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_job"


def test_setup_logger_stream_handler_added():
    config = LogConfig(job_name="test_stream")
    logger = setup_logger(config)
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


def test_setup_logger_file_handler_added(tmp_path):
    log_file = str(tmp_path / "cronwrap.log")
    config = LogConfig(job_name="test_file", log_file=log_file)
    logger = setup_logger(config)
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)


def test_log_run_result_success(caplog):
    config = LogConfig(job_name="myjob", log_level="DEBUG")
    logger = setup_logger(config)
    result = _make_result(success=True, returncode=0, duration=2.5, stdout="ok")
    with caplog.at_level(logging.DEBUG, logger="myjob"):
        log_run_result(logger, result, attempt=1)
    assert "SUCCESS" in caplog.text
    assert "attempt=1" in caplog.text


def test_log_run_result_failure(caplog):
    config = LogConfig(job_name="myjob2")
    logger = setup_logger(config)
    result = _make_result(success=False, returncode=1, duration=0.5, stderr="oops")
    with caplog.at_level(logging.ERROR, logger="myjob2"):
        log_run_result(logger, result, attempt=2)
    assert "FAILURE" in caplog.text


def test_log_run_result_timeout(caplog):
    config = LogConfig(job_name="myjob3")
    logger = setup_logger(config)
    result = _make_result(success=False, timed_out=True)
    with caplog.at_level(logging.ERROR, logger="myjob3"):
        log_run_result(logger, result)
    assert "timed out" in caplog.text
