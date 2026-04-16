import os
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.logger import LogConfig


@dataclass
class CronwrapConfig:
    command: List[str] = field(default_factory=list)
    retries: int = 0
    timeout: Optional[float] = None
    job_name: str = "cronwrap"
    log_file: Optional[str] = None
    log_level: str = "INFO"
    notify_on_failure: bool = True
    notify_on_success: bool = False

    def log_config(self) -> LogConfig:
        return LogConfig(
            log_file=self.log_file,
            log_level=self.log_level,
            job_name=self.job_name,
        )


def from_args(args) -> CronwrapConfig:
    """Build a CronwrapConfig from parsed CLI args (argparse.Namespace)."""
    return CronwrapConfig(
        command=args.command,
        retries=getattr(args, "retries", 0),
        timeout=getattr(args, "timeout", None),
        job_name=getattr(args, "job_name", "cronwrap"),
        log_file=getattr(args, "log_file", None),
        log_level=getattr(args, "log_level", "INFO"),
        notify_on_failure=getattr(args, "notify_on_failure", True),
        notify_on_success=getattr(args, "notify_on_success", False),
    )


def from_env(base: Optional[CronwrapConfig] = None) -> CronwrapConfig:
    """Override config fields from environment variables."""
    cfg = base or CronwrapConfig()
    if val := os.getenv("CRONWRAP_JOB_NAME"):
        cfg.job_name = val
    if val := os.getenv("CRONWRAP_LOG_FILE"):
        cfg.log_file = val
    if val := os.getenv("CRONWRAP_LOG_LEVEL"):
        cfg.log_level = val
    if val := os.getenv("CRONWRAP_RETRIES"):
        cfg.retries = int(val)
    if val := os.getenv("CRONWRAP_TIMEOUT"):
        cfg.timeout = float(val)
    return cfg
