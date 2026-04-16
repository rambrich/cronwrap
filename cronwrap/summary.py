"""Aggregate run summaries from history for reporting."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from cronwrap.history import HistoryEntry


@dataclass
class RunSummary:
    job_name: Optional[str]
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_duration: float
    min_duration: float
    max_duration: float
    last_status: Optional[bool]
    last_started_at: Optional[str]

    def as_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": round(self.success_rate, 4),
            "avg_duration": round(self.avg_duration, 3),
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "last_status": self.last_status,
            "last_started_at": self.last_started_at,
        }


def summarize(entries: List[HistoryEntry], job_name: Optional[str] = None) -> RunSummary:
    if not entries:
        return RunSummary(
            job_name=job_name, total_runs=0, successful_runs=0, failed_runs=0,
            success_rate=0.0, avg_duration=0.0, min_duration=0.0, max_duration=0.0,
            last_status=None, last_started_at=None,
        )
    total = len(entries)
    successes = sum(1 for e in entries if e.success)
    durations = [e.duration for e in entries]
    last = entries[-1]
    return RunSummary(
        job_name=job_name or last.job_name,
        total_runs=total,
        successful_runs=successes,
        failed_runs=total - successes,
        success_rate=successes / total,
        avg_duration=sum(durations) / total,
        min_duration=min(durations),
        max_duration=max(durations),
        last_status=last.success,
        last_started_at=last.started_at,
    )
