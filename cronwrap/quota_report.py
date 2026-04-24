"""Quota usage report rendering for cronwrap."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any


def _load_all_states(state_dir: str) -> List[Dict[str, Any]]:
    """Load all quota state files from the given directory."""
    p = Path(state_dir)
    if not p.exists():
        return []
    states = []
    for f in sorted(p.glob("quota_*.json")):
        try:
            data = json.loads(f.read_text())
            data.setdefault("_file", f.stem)
            states.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return states


def summarize_states(states: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Produce a summary dict from a list of quota states."""
    if not states:
        return {"total_jobs": 0, "exhausted": 0, "within_quota": 0}
    exhausted = sum(1 for s in states if s.get("count", 0) >= s.get("limit", 1))
    return {
        "total_jobs": len(states),
        "exhausted": exhausted,
        "within_quota": len(states) - exhausted,
    }


def render_report(states: List[Dict[str, Any]]) -> str:
    """Render a human-readable quota report."""
    summary = summarize_states(states)
    lines = [
        "=== Quota Report ===",
        f"Total jobs tracked : {summary['total_jobs']}",
        f"Within quota       : {summary['within_quota']}",
        f"Exhausted          : {summary['exhausted']}",
        "",
    ]
    if states:
        lines.append(f"{'Job':<30} {'Count':>6} {'Limit':>6} {'Status':<10}")
        lines.append("-" * 58)
        for s in states:
            job = s.get("job", s.get("_file", "unknown"))
            count = s.get("count", 0)
            limit = s.get("limit", "?")
            status = "EXHAUSTED" if isinstance(limit, int) and count >= limit else "ok"
            lines.append(f"{job:<30} {count:>6} {str(limit):>6} {status:<10}")
    return "\n".join(lines)


def print_report(state_dir: str) -> None:
    """Load states from *state_dir* and print the report to stdout."""
    states = _load_all_states(state_dir)
    print(render_report(states))
