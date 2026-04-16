"""Configuration aggregation for cronwrap."""
from dataclasses import dataclass
from typing import Optional
import os

from cronwrap.logger import LogConfig
from cronwrap.metrics import MetricsConfig


@dataclass
class CronwrapConfig:
    job_name: str
    retries: int
    timeout: Optional[float]
    log_config: LogConfig
    metrics_config: MetricsConfig

    @classmethod
    def from_args(cls, args) -> "CronwrapConfig":
        log_config = LogConfig(
            log_file=getattr(args, "log_file", None),
            log_level=getattr(args, "log_level", "INFO"),
        )
        metrics_config = MetricsConfig(
            metrics_file=getattr(args, "metrics_file", None),
            enabled=bool(getattr(args, "metrics_file", None)),
        )
        return cls(
            job_name=getattr(args, "job_name", "cron-job"),
            retries=getattr(args, "retries", 0),
            timeout=getattr(args, "timeout", None),
            log_config=log_config,
            metrics_config=metrics_config,
        )

    @classmethod
    def from_env(cls) -> "CronwrapConfig":
        log_config = LogConfig(
            log_file=os.environ.get("CRONWRAP_LOG_FILE"),
            log_level=os.environ.get("CRONWRAP_LOG_LEVEL", "INFO"),
        )
        metrics_config = MetricsConfig.from_env()
        timeout_raw = os.environ.get("CRONWRAP_TIMEOUT")
        return cls(
            job_name=os.environ.get("CRONWRAP_JOB_NAME", "cron-job"),
            retries=int(os.environ.get("CRONWRAP_RETRIES", "0")),
            timeout=float(timeout_raw) if timeout_raw else None,
            log_config=log_config,
            metrics_config=metrics_config,
        )
