"""CLI for inspecting and managing drift state."""
from __future__ import annotations

import argparse
import sys
import time

from cronwrap.drift import DriftConfig, DriftManager
from cronwrap.drift_report import print_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cronwrap-drift", description="Drift detection management")
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show drift status for a job")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Reset drift state for a job")
    reset_p.add_argument("job", help="Job name")

    mark_p = sub.add_parser("mark", help="Record expected run time for a job (defaults to now)")
    mark_p.add_argument("job", help="Job name")
    mark_p.add_argument("--at", type=float, default=None, help="Expected timestamp (unix epoch)")

    sub.add_parser("report", help="Print drift summary report")

    return parser


def _manager() -> DriftManager:
    return DriftManager(DriftConfig.from_env())


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager()
    if not mgr.config.enabled:
        print("Drift detection is disabled.")
        return
    result = mgr.check(args.job, actual_at=time.time())
    if result is None:
        print(f"No drift state recorded for job '{args.job}'.")
        return
    print(f"Job            : {result.job}")
    print(f"Expected at    : {result.expected_at:.2f}")
    print(f"Actual at      : {result.actual_at:.2f}")
    print(f"Drift (s)      : {result.drift_seconds:.2f}")
    print(f"Warning        : {'yes' if result.is_warning else 'no'}")
    print(f"Critical       : {'yes' if result.is_critical else 'no'}")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager()
    mgr.reset(args.job)
    print(f"Drift state reset for job '{args.job}'.")


def cmd_mark(args: argparse.Namespace) -> None:
    mgr = _manager()
    if not mgr.config.enabled:
        print("Drift detection is disabled.")
        return
    mgr.record_expected(args.job, expected_at=args.at)
    ts = args.at if args.at is not None else time.time()
    print(f"Expected run time recorded for '{args.job}': {ts:.2f}")


def cmd_report(args: argparse.Namespace) -> None:
    cfg = DriftConfig.from_env()
    print_report(cfg.state_dir)


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"status": cmd_status, "reset": cmd_reset, "mark": cmd_mark, "report": cmd_report}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
