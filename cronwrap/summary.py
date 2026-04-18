"""Run summary aggregation for cronwrap pipeline output."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from cronwrap.runner import RunResult


@dataclass
class RunSummary:
    job_name: str
    success: bool
    exit_code: int
    duration: float
    retries: int = 0
    tags: List[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "job_name": self.job_name,
            "success": self.success,
            "exit_code": self.exit_code,
            "duration": round(self.duration, 3),
            "retries": self.retries,
            "tags": self.tags,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            **self.extra,
        }


def summarize(
    result: RunResult,
    job_name: str = "",
    retries: int = 0,
    tags: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> RunSummary:
    """Build a RunSummary from a RunResult and optional metadata."""
    return RunSummary(
        job_name=job_name,
        success=result.success,
        exit_code=result.exit_code,
        duration=result.duration,
        retries=retries,
        tags=tags or [],
        stdout=result.stdout,
        stderr=result.stderr,
        error=result.error,
        extra=extra or {},
    )
