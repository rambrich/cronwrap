"""CLI for inspecting and resetting cadence state."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from cronwrap.cadence import CadenceConfig, CadenceManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-cadence",
        description="Inspect and manage cadence tracking state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show cadence state for a job")
    status_p.add_argument("--job-id", default="default", help="Job identifier")
    status_p.add_argument("--state-dir", default="/tmp/cronwrap/cadence")

    reset_p = sub.add_parser("reset", help="Reset cadence state for a job")
    reset_p.add_argument("--job-id", default="default", help="Job identifier")
    reset_p.add_argument("--state-dir", default="/tmp/cronwrap/cadence")

    return parser


def _manager(args: argparse.Namespace) -> CadenceManager:
    cfg = CadenceConfig(
        enabled=True,
        state_dir=args.state_dir,
        job_id=args.job_id,
    )
    return CadenceManager(cfg)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    p = mgr._state_path()
    if not p.exists():
        print(f"No cadence state found for job '{args.job_id}'.")
        return
    data = json.loads(p.read_text())
    last_ts = data.get("last_run_ts")
    if last_ts:
        elapsed = time.time() - last_ts
        print(f"Job:       {args.job_id}")
        print(f"Last run:  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_ts))}")
        print(f"Elapsed:   {elapsed:.1f}s ago")
    else:
        print("State file exists but contains no timestamp.")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    mgr.reset()
    print(f"Cadence state reset for job '{args.job_id}'.")


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
