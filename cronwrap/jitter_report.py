"""Report generation for jitter tracking across job runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import json
import statistics


@dataclass
class JitterSummary:
    job_name: str
    sample_count: int
    min_seconds: float
    max_seconds: float
    mean_seconds: float
    stddev_seconds: float
    samples: List[float] = field(default_factory=list)


def _load_all_samples(state_dir: Path) -> dict[str, List[float]]:
    results: dict[str, List[float]] = {}
    if not state_dir.exists():
        return results
    for path in state_dir.glob("jitter_*.json"):
        try:
            data = json.loads(path.read_text())
            job = data.get("job", path.stem)
            samples = [float(s) for s in data.get("samples", [])]
            if samples:
                results[job] = samples
        except Exception:
            continue
    return results


def summarize_samples(state_dir: Path) -> List[JitterSummary]:
    all_samples = _load_all_samples(state_dir)
    summaries = []
    for job, samples in sorted(all_samples.items()):
        summaries.append(
            JitterSummary(
                job_name=job,
                sample_count=len(samples),
                min_seconds=min(samples),
                max_seconds=max(samples),
                mean_seconds=statistics.mean(samples),
                stddev_seconds=statistics.stdev(samples) if len(samples) > 1 else 0.0,
                samples=samples,
            )
        )
    return summaries


def render_report(summaries: List[JitterSummary]) -> str:
    if not summaries:
        return "No jitter data available.\n"
    lines = ["Jitter Report", "=" * 50]
    for s in summaries:
        lines.append(f"\nJob: {s.job_name}")
        lines.append(f"  Samples : {s.sample_count}")
        lines.append(f"  Min     : {s.min_seconds:.3f}s")
        lines.append(f"  Max     : {s.max_seconds:.3f}s")
        lines.append(f"  Mean    : {s.mean_seconds:.3f}s")
        lines.append(f"  StdDev  : {s.stddev_seconds:.3f}s")
    return "\n".join(lines) + "\n"


def print_report(state_dir: Path) -> None:
    summaries = summarize_samples(state_dir)
    print(render_report(summaries))
