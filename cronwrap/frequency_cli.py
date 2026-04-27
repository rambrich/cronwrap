"""CLI for inspecting and resetting frequency tracking state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.frequency import FrequencyConfig, FrequencyManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-frequency",
        description="Inspect and manage job frequency tracking.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show frequency state for a job")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Reset frequency state for a job")
    reset_p.add_argument("job", help="Job name")

    sub.add_parser("list", help="List all tracked jobs")
    return parser


def _manager(job: str) -> FrequencyManager:
    return FrequencyManager(FrequencyConfig.from_env(), job)


def cmd_status(args: argparse.Namespace) -> None:
    import time

    mgr = _manager(args.job)
    cfg = mgr.config
    if not cfg.enabled:
        print("Frequency tracking is disabled.")
        return
    timestamps = mgr._load_timestamps()
    now = time.time()
    cutoff = now - cfg.window_seconds
    recent = [t for t in timestamps if t >= cutoff]
    count = len(recent)
    print(f"Job:            {args.job}")
    print(f"Window:         {cfg.window_seconds}s")
    print(f"Runs in window: {count}")
    print(f"Min runs:       {cfg.min_runs}")
    print(f"Max runs:       {cfg.max_runs}")
    if count > cfg.max_runs:
        print("Status:         TOO FREQUENT")
    elif count < cfg.min_runs:
        print("Status:         TOO INFREQUENT")
    else:
        print("Status:         OK")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    mgr.reset()
    print(f"Frequency state reset for job: {args.job}")


def cmd_list(args: argparse.Namespace) -> None:
    cfg = FrequencyConfig.from_env()
    state_dir = Path(cfg.state_dir)
    if not state_dir.exists():
        print("No frequency state found.")
        return
    files = sorted(state_dir.glob("*.json"))
    if not files:
        print("No tracked jobs.")
        return
    for f in files:
        print(f.stem)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
