"""CLI for inspecting trendline state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.trendline import TrendlineConfig, TrendlineManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cronwrap-trendline", description="Trendline analysis tool")
    sub = parser.add_subparsers(dest="command")

    status_p = sub.add_parser("status", help="Show current trend for a job")
    status_p.add_argument("--job", default="default", help="Job name")

    reset_p = sub.add_parser("reset", help="Clear trendline state for a job")
    reset_p.add_argument("--job", default="default", help="Job name")

    return parser


def _manager(job: str) -> TrendlineManager:
    config = TrendlineConfig.from_env()
    return TrendlineManager(config, job_name=job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    durations = mgr._load_durations()
    if not durations:
        print(f"No trendline data for job '{args.job}'.")
        return
    result = mgr.analyze(durations)
    print(f"Job:       {args.job}")
    print(f"Direction: {result.direction}")
    print(f"Samples:   {len(durations)}")
    if result.average_before is not None:
        print(f"Avg before: {result.average_before:.2f}s")
    if result.average_after is not None:
        print(f"Avg after:  {result.average_after:.2f}s")
    if result.change_pct is not None:
        print(f"Change:    {result.change_pct * 100:+.1f}%")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    p = mgr._state_path()
    if p.exists():
        p.unlink()
        print(f"Trendline state reset for job '{args.job}'.")
    else:
        print(f"No state found for job '{args.job}'.")


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
