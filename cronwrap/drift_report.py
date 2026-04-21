"""Drift report: summarize and render drift results from persisted state."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from cronwrap.drift import DriftResult


def load_drift_results(state_dir: str) -> List[dict]:
    """Load all persisted drift state entries from state_dir."""
    results = []
    p = Path(state_dir)
    if not p.exists():
        return results
    for f in sorted(p.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            data.setdefault("job", f.stem)
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results


def summarize_results(results: List[dict]) -> dict:
    total = len(results)
    warnings = sum(1 for r in results if r.get("is_warning"))
    criticals = sum(1 for r in results if r.get("is_critical"))
    drifts = [r.get("drift_seconds", 0.0) for r in results]
    avg_drift = sum(drifts) / total if total else 0.0
    max_drift = max(drifts) if drifts else 0.0
    return {
        "total": total,
        "warnings": warnings,
        "criticals": criticals,
        "avg_drift_seconds": round(avg_drift, 2),
        "max_drift_seconds": round(max_drift, 2),
    }


def render_report(results: List[dict]) -> str:
    summary = summarize_results(results)
    lines = [
        "=== Drift Report ===",
        f"Total jobs tracked : {summary['total']}",
        f"Warnings           : {summary['warnings']}",
        f"Criticals          : {summary['criticals']}",
        f"Avg drift (s)      : {summary['avg_drift_seconds']}",
        f"Max drift (s)      : {summary['max_drift_seconds']}",
        "",
    ]
    if results:
        lines.append(f"{'Job':<30} {'Drift (s)':>10} {'Warn':>6} {'Crit':>6}")
        lines.append("-" * 56)
        for r in results:
            warn = "yes" if r.get("is_warning") else "no"
            crit = "yes" if r.get("is_critical") else "no"
            lines.append(f"{r.get('job', ''):<30} {r.get('drift_seconds', 0.0):>10.2f} {warn:>6} {crit:>6}")
    return "\n".join(lines)


def print_report(state_dir: str) -> None:
    results = load_drift_results(state_dir)
    print(render_report(results))
