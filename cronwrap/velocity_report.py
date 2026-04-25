"""Report utilities for velocity state files."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class VelocitySummary:
    total_jobs: int
    spike_jobs: List[str]
    avg_rate_per_hour: float


def _load_all_states(state_dir: str) -> List[dict]:
    p = Path(state_dir)
    if not p.exists():
        return []
    results = []
    for f in sorted(p.glob("*.json")):
        try:
            timestamps = json.loads(f.read_text())
            job = f.stem
            results.append({"job": job, "timestamps": timestamps})
        except Exception:
            continue
    return results


def summarize_states(state_dir: str, window_seconds: int = 3600) -> VelocitySummary:
    states = _load_all_states(state_dir)
    if not states:
        return VelocitySummary(total_jobs=0, spike_jobs=[], avg_rate_per_hour=0.0)

    rates = []
    for s in states:
        count = len(s["timestamps"])
        rate = count / (window_seconds / 3600.0)
        rates.append(rate)

    avg = sum(rates) / len(rates) if rates else 0.0
    spike_jobs = [
        s["job"] for s, r in zip(states, rates) if r > avg * 2 and avg > 0
    ]
    return VelocitySummary(
        total_jobs=len(states),
        spike_jobs=spike_jobs,
        avg_rate_per_hour=round(avg, 4),
    )


def render_report(summary: VelocitySummary) -> str:
    lines = [
        "=== Velocity Report ===",
        f"Total jobs tracked : {summary.total_jobs}",
        f"Avg rate/hour      : {summary.avg_rate_per_hour}",
        f"Spike jobs         : {', '.join(summary.spike_jobs) if summary.spike_jobs else 'none'}",
    ]
    return "\n".join(lines)


def print_report(state_dir: str, window_seconds: int = 3600) -> None:
    summary = summarize_states(state_dir, window_seconds)
    print(render_report(summary))
