"""CLI for inspecting and managing rate limit state."""
from __future__ import annotations

import argparse
import json
import os
import sys

from cronwrap.ratelimit import RateLimitConfig, RateLimiter
from cronwrap.ratelimit_report import print_report, _load_all_states, summarize_states


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-ratelimit",
        description="Inspect and manage cronwrap rate limit state",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show rate limit status for all tracked jobs")

    reset_p = sub.add_parser("reset", help="Reset rate limit state for a job")
    reset_p.add_argument("job", help="Job name (used as key)")

    sub.add_parser("report", help="Print aggregated rate limit report")

    return parser


def _state_dir() -> str:
    return os.environ.get("CRONWRAP_STATE_DIR", "/tmp/cronwrap")


def cmd_status(args: argparse.Namespace) -> None:
    state_dir = _state_dir()
    states = _load_all_states(state_dir)
    if not states:
        print("No rate limit state found.")
        return
    for s in states:
        job = s.get("_job", "unknown")
        count = s.get("count", 0)
        blocked = s.get("blocked", False)
        status = "BLOCKED" if blocked else "ok"
        print(f"{job}: count={count} status={status}")


def cmd_reset(args: argparse.Namespace) -> None:
    state_dir = _state_dir()
    fname = os.path.join(state_dir, f"{args.job}.ratelimit.json")
    if os.path.exists(fname):
        os.remove(fname)
        print(f"Reset rate limit state for job: {args.job}")
    else:
        print(f"No state found for job: {args.job}")


def cmd_report(args: argparse.Namespace) -> None:
    print_report(_state_dir())


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"status": cmd_status, "reset": cmd_reset, "report": cmd_report}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
