"""Report utilities for spike detection history."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Optional


def _load_all_histories(state_dir: str) -> Dict[str, List[float]]:
    """Load all spike history files from state_dir."""
    result: Dict[str, List[float]] = {}
    p = Path(state_dir)
    if not p.exists():
        return result
    for f in sorted(p.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            if isinstance(data, list):
                result[f.stem] = data
        except (json.JSONDecodeError, OSError):
            continue
    return result


def summarize_histories(state_dir: str) -> List[dict]:
    """Return a summary row per job."""
    histories = _load_all_histories(state_dir)
    rows = []
    for job, durations in histories.items():
        if not durations:
            continue
        row: dict = {
            "job": job,
            "samples": len(durations),
            "mean": round(mean(durations), 4),
            "min": round(min(durations), 4),
            "max": round(max(durations), 4),
            "stdev": round(stdev(durations), 4) if len(durations) >= 2 else None,
        }
        rows.append(row)
    return rows


def render_report(state_dir: str) -> str:
    rows = summarize_histories(state_dir)
    if not rows:
        return "No spike history data found."

    lines = ["Spike Detection Report", "=" * 50]
    header = f"{'Job':<25} {'Samples':>7} {'Mean':>8} {'Min':>8} {'Max':>8} {'StdDev':>8}"
    lines.append(header)
    lines.append("-" * 70)
    for r in rows:
        sd = f"{r['stdev']:.3f}" if r["stdev"] is not None else "  N/A"
        lines.append(
            f"{r['job']:<25} {r['samples']:>7} {r['mean']:>8.3f} {r['min']:>8.3f} {r['max']:>8.3f} {sd:>8}"
        )
    return "\n".join(lines)


def print_report(state_dir: str) -> None:
    print(render_report(state_dir))
