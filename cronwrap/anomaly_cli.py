"""CLI for inspecting anomaly detection state."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from cronwrap.anomaly import AnomalyConfig, AnomalyDetector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-anomaly",
        description="Inspect anomaly detection history",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show history stats for a job")
    status_p.add_argument("--job", default="default", help="Job ID")

    reset_p = sub.add_parser("reset", help="Clear history for a job")
    reset_p.add_argument("--job", default="default", help="Job ID")

    return parser


def _manager(job: str) -> AnomalyDetector:
    config = AnomalyConfig.from_env()
    return AnomalyDetector(config, job_id=job)


def cmd_status(args: argparse.Namespace) -> None:
    det = _manager(args.job)
    history = det._load_history()
    if not history:
        print(f"No history found for job '{args.job}'.")
        return
    mean = statistics.mean(history)
    stddev = statistics.pstdev(history)
    print(f"Job:     {args.job}")
    print(f"Samples: {len(history)}")
    print(f"Mean:    {mean:.4f}s")
    print(f"Stddev:  {stddev:.4f}s")
    print(f"Min:     {min(history):.4f}s")
    print(f"Max:     {max(history):.4f}s")


def cmd_reset(args: argparse.Namespace) -> None:
    det = _manager(args.job)
    p = det._state_path()
    if p.exists():
        p.unlink()
        print(f"Cleared anomaly history for job '{args.job}'.")
    else:
        print(f"No history to clear for job '{args.job}'.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)


if __name__ == "__main__":
    main()
