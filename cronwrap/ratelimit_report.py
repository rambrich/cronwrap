"""Report renderer for rate limit state across jobs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List


@dataclass
class RateLimitSummary:
    total_jobs: int
    active_jobs: int
    total_requests: int
    blocked_jobs: List[str]


def _load_all_states(state_dir: str) -> List[dict]:
    states = []
    if not os.path.isdir(state_dir):
        return states
    for fname in os.listdir(state_dir):
        if not fname.endswith(".ratelimit.json"):
            continue
        fpath = os.path.join(state_dir, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
                data["_job"] = fname.replace(".ratelimit.json", "")
                states.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return states


def summarize_states(states: List[dict]) -> RateLimitSummary:
    if not states:
        return RateLimitSummary(0, 0, 0, [])
    blocked = [s["_job"] for s in states if s.get("blocked", False)]
    total_requests = sum(s.get("count", 0) for s in states)
    active = sum(1 for s in states if s.get("count", 0) > 0)
    return RateLimitSummary(
        total_jobs=len(states),
        active_jobs=active,
        total_requests=total_requests,
        blocked_jobs=blocked,
    )


def render_report(summary: RateLimitSummary) -> str:
    lines = [
        "=== Rate Limit Report ===",
        f"Total jobs tracked : {summary.total_jobs}",
        f"Active jobs        : {summary.active_jobs}",
        f"Total requests     : {summary.total_requests}",
        f"Blocked jobs       : {len(summary.blocked_jobs)}",
    ]
    if summary.blocked_jobs:
        lines.append("Blocked job list:")
        for job in summary.blocked_jobs:
            lines.append(f"  - {job}")
    return "\n".join(lines)


def print_report(state_dir: str = "/tmp/cronwrap") -> None:
    states = _load_all_states(state_dir)
    summary = summarize_states(states)
    print(render_report(summary))
