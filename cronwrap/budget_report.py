"""Simple budget usage report across multiple jobs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any


def _load_all_states(state_dir: str) -> List[Dict[str, Any]]:
    """Load all budget state files from state_dir."""
    results = []
    for path in sorted(Path(state_dir).glob("budget_*.json")):
        try:
            data = json.loads(path.read_text())
            job_name = path.stem[len("budget_"):]
            data["job"] = job_name
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results


def render_report(states: List[Dict[str, Any]], limit: float = 3600.0) -> str:
    if not states:
        return "No budget data found.\n"
    lines = [f"{'Job':<25} {'Date':<12} {'Used (s)':>10} {'Limit (s)':>10} {'Remaining':>10}"]
    lines.append("-" * 72)
    for s in states:
        used = s.get("total_seconds", 0.0)
        remaining = max(0.0, limit - used)
        lines.append(
            f"{s['job']:<25} {s.get('date','?'):<12} {used:>10.1f} {limit:>10.1f} {remaining:>10.1f}"
        )
    return "\n".join(lines) + "\n"


def print_report(state_dir: str = "/tmp/cronwrap", limit: float = 3600.0) -> None:
    states = _load_all_states(state_dir)
    print(render_report(states, limit=limit))
