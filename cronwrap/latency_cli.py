"""CLI for inspecting latency state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.latency import LatencyConfig, LatencyManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-latency",
        description="Inspect and manage latency tracking state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show latency state for a job")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Clear latency state for a job")
    reset_p.add_argument("job", help="Job name")

    return parser


def _manager(job: str) -> LatencyManager:
    cfg = LatencyConfig.from_env()
    return LatencyManager(cfg, job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    samples = mgr._load_samples()
    if not samples:
        print(f"No latency data for job '{args.job}'.")
        return
    avg = sum(samples) / len(samples)
    print(f"Job:          {args.job}")
    print(f"Samples:      {len(samples)}")
    print(f"Avg duration: {avg:.2f}s")
    print(f"Min:          {min(samples):.2f}s")
    print(f"Max:          {max(samples):.2f}s")
    print(f"Warn thresh:  {mgr.config.warn_seconds}s")
    print(f"Crit thresh:  {mgr.config.crit_seconds}s")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    mgr.reset()
    print(f"Latency state cleared for job '{args.job}'.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
