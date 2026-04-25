"""CLI for inspecting percentile data."""
from __future__ import annotations

import argparse
import sys

from cronwrap.percentile import PercentileConfig, PercentileManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-percentile",
        description="Inspect run duration percentiles per job.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show percentiles for a job")
    status_p.add_argument("job", help="Job identifier (command string)")

    reset_p = sub.add_parser("reset", help="Clear percentile samples for a job")
    reset_p.add_argument("job", help="Job identifier (command string)")

    return parser


def _manager() -> PercentileManager:
    return PercentileManager(PercentileConfig.from_env())


def cmd_status(args: argparse.Namespace, mgr: PercentileManager | None = None) -> None:
    if mgr is None:
        mgr = _manager()
    if not mgr.config.enabled:
        print("Percentile tracking is disabled. Set CRONWRAP_PERCENTILE_ENABLED=true to enable.")
        return
    result = mgr.get(args.job)
    if result is None:
        print(f"No percentile data found for job: {args.job}")
        return
    print(f"Job           : {result.job}")
    print(f"Samples       : {result.sample_count}")
    if result.p50 is not None:
        print(f"p50 (median)  : {result.p50:.4f}s")
    if result.p95 is not None:
        print(f"p95           : {result.p95:.4f}s")
    if result.p99 is not None:
        print(f"p99           : {result.p99:.4f}s")


def cmd_reset(args: argparse.Namespace, mgr: PercentileManager | None = None) -> None:
    if mgr is None:
        mgr = _manager()
    if not mgr.config.enabled:
        print("Percentile tracking is disabled.")
        return
    mgr.reset(args.job)
    print(f"Percentile samples cleared for job: {args.job}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    mgr = _manager()
    if args.command == "status":
        cmd_status(args, mgr)
    elif args.command == "reset":
        cmd_reset(args, mgr)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
