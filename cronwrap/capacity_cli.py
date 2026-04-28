"""CLI for inspecting capacity state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.capacity import CapacityConfig, CapacityManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cronwrap-capacity", description="Inspect capacity tracking state")
    sub = parser.add_subparsers(dest="command")

    status_p = sub.add_parser("status", help="Show capacity state for a job")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Reset capacity state for a job")
    reset_p.add_argument("job", help="Job name")

    return parser


def _manager(job: str) -> CapacityManager:
    config = CapacityConfig.from_env()
    return CapacityManager(config, job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    p = mgr._state_path()
    if not p.exists():
        print(f"No capacity data for job '{args.job}'.")
        return
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error reading state: {exc}", file=sys.stderr)
        sys.exit(1)
    samples = data.get("samples", [])
    if not samples:
        print(f"No samples recorded for job '{args.job}'.")
        return
    historical_max = max(samples)
    avg = sum(samples) / len(samples)
    print(f"Job:           {args.job}")
    print(f"Samples:       {len(samples)}")
    print(f"Historical max:{historical_max:.3f}s")
    print(f"Average:       {avg:.3f}s")
    print(f"Last sample:   {samples[-1]:.3f}s")
    cfg = mgr.config
    utilization = samples[-1] / historical_max if historical_max > 0 else 0.0
    print(f"Utilization:   {utilization * 100:.1f}%  (warn >= {cfg.warn_threshold * 100:.0f}%)")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    p = mgr._state_path()
    if p.exists():
        p.unlink()
        print(f"Capacity state reset for job '{args.job}'.")
    else:
        print(f"No capacity state found for job '{args.job}'.")


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
