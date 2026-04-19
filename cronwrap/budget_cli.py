"""CLI for inspecting and resetting execution budget state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.budget import BudgetConfig, BudgetManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-budget",
        description="Inspect or reset the daily execution budget for a job.",
    )
    parser.add_argument("--job", default="default", help="Job name (default: default)")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("status", help="Show current budget usage")
    sub.add_parser("reset", help="Reset budget state for today")
    return parser


def _manager(job: str) -> BudgetManager:
    cfg = BudgetConfig.from_env()
    cfg.enabled = True  # CLI always operates regardless of env flag
    return BudgetManager(cfg, job_name=job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    state = mgr._load_state()
    remaining = mgr.remaining()
    print(f"Job       : {args.job}")
    print(f"Date      : {state.date}")
    print(f"Used      : {state.total_seconds:.1f}s")
    print(f"Limit     : {mgr.config.max_seconds_per_day:.1f}s")
    print(f"Remaining : {remaining:.1f}s")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    path = mgr._state_path()
    if path.exists():
        path.unlink()
        print(f"Budget state reset for job '{args.job}'.")
    else:
        print(f"No budget state found for job '{args.job}'.")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "reset":
        cmd_reset(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
