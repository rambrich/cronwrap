"""Cron expression validation and next-run scheduling utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

try:
    from croniter import croniter
    _CRONITER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CRONITER_AVAILABLE = False


@dataclass
class ScheduleConfig:
    expression: Optional[str] = None
    enabled: bool = False

    @classmethod
    def from_env(cls, env: dict) -> "ScheduleConfig":
        expr = env.get("CRONWRAP_SCHEDULE")
        return cls(expression=expr, enabled=bool(expr))


def validate_expression(expression: str) -> bool:
    """Return True if *expression* is a valid 5-field cron expression."""
    if not _CRONITER_AVAILABLE:
        parts = expression.strip().split()
        return len(parts) == 5
    return croniter.is_valid(expression)


def next_run(expression: str, base: Optional[datetime] = None) -> Optional[datetime]:
    """Return the next datetime after *base* (default: now) for *expression*."""
    if not validate_expression(expression):
        return None
    if not _CRONITER_AVAILABLE:
        return None
    base = base or datetime.now()
    return croniter(expression, base).get_next(datetime)


def seconds_until_next_run(expression: str, base: Optional[datetime] = None) -> Optional[float]:
    """Return seconds until the next scheduled run, or None on invalid expression."""
    nxt = next_run(expression, base)
    if nxt is None:
        return None
    base = base or datetime.now()
    return max(0.0, (nxt - base).total_seconds())
