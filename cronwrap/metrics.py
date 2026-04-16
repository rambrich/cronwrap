"""Metrics collection for cron job runs."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import json
import os

from cronwrap.runner import RunResult


@dataclass
class RunMetric:
    job_name: str
    exit_code: int
    duration_seconds: float
    retries: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    success: bool = False

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "retries": self.retries,
            "timestamp": self.timestamp,
            "success": self.success,
        }


@dataclass
class MetricsConfig:
    metrics_file: Optional[str] = None
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "MetricsConfig":
        metrics_file = os.environ.get("CRONWRAP_METRICS_FILE")
        return cls(metrics_file=metrics_file, enabled=bool(metrics_file))


class MetricsCollector:
    def __init__(self, config: MetricsConfig):
        self.config = config
        self._records: List[RunMetric] = []

    def record(self, job_name: str, result: RunResult, retries: int = 0) -> RunMetric:
        metric = RunMetric(
            job_name=job_name,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
            retries=retries,
            success=result.exit_code == 0,
        )
        self._records.append(metric)
        if self.config.enabled and self.config.metrics_file:
            self._append_to_file(metric)
        return metric

    def _append_to_file(self, metric: RunMetric) -> None:
        with open(self.config.metrics_file, "a") as f:
            f.write(json.dumps(metric.to_dict()) + "\n")

    def get_records(self) -> List[RunMetric]:
        return list(self._records)
