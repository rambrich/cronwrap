import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LogConfig:
    log_file: Optional[str] = None
    log_level: str = "INFO"
    job_name: str = "cronwrap"


def setup_logger(config: LogConfig) -> logging.Logger:
    logger = logging.getLogger(config.job_name)
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_run_result(logger: logging.Logger, result, attempt: int = 1) -> None:
    """Log a RunResult from cronwrap.runner."""
    status = "SUCCESS" if result.success else "FAILURE"
    logger.info(
        "job=%s attempt=%d status=%s exit_code=%d duration=%.2fs",
        logger.name,
        attempt,
        status,
        result.returncode,
        result.duration,
    )
    if result.stdout:
        logger.debug("stdout: %s", result.stdout.strip())
    if result.stderr:
        level = logging.WARNING if result.success else logging.ERROR
        logger.log(level, "stderr: %s", result.stderr.strip())
    if result.timed_out:
        logger.error("job=%s timed out", logger.name)
