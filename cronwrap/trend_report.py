"""Render a summary report from trend state files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List


def _load_all_trends(state_dir: str) -> List[dict]:
    """Return list of {job, history} dicts from the state directory."""
    p = Path(state_dir)
    if not p.exists():
        return []
    results = []
    for f in sorted(p.glob("*.json")):
        try:
            history: List[int] = json.loads(f.read_text())
            results.append({"job": f.stem, "history": history})
        except (json.JSONDecodeError, OSError):
            continue
    return results


def summarize_trends(state_dir: str, window: int = 20) -> List[dict]:
    rows = []
    for entry in _load_all_trends(state_dir):
        history = entry["history"]
        window_slice = history[-window:]
        rate = sum(window_slice) / len(window_slice) if window_slice else 1.0
        rows.append({
            "job": entry["job"],
            "total_runs": len(history),
            "window_runs": len(window_slice),
            "success_rate": round(rate, 4),
            "degrading": rate < 0.5,
        })
    return rows


def render_report(state_dir: str, window: int = 20) -> str:
    rows = summarize_trends(state_dir, window)
    if not rows:
        return "No trend data found.\n"
    lines = [f"{'Job':<30} {'Runs':>6} {'Window':>7} {'Rate':>7} {'Status'}",
             "-" * 62]
    for r in rows:
        status = "DEGRADING" if r["degrading"] else "ok"
        lines.append(
            f"{r['job']:<30} {r['total_runs']:>6} {r['window_runs']:>7}"
            f" {r['success_rate']:>7.1%} {status}"
        )
    return "\n".join(lines) + "\n"


def print_report(state_dir: str, window: int = 20) -> None:
    print(render_report(state_dir, window), end="")
