"""CLI commands for inspecting jitter state and reports."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from cronwrap.jitter import JitterConfig, JitterManager
from cronwrap.jitter_report import print_report, summarize_samples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-jitter",
        description="Inspect and report on jitter configuration and history.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current jitter configuration.")

    report_p = sub.add_parser("report", help="Print jitter report from state files.")
    report_p.add_argument(
        "--state-dir",
        default=os.environ.get("CRONWRAP_STATE_DIR", "/tmp/cronwrap"),
        help="Directory containing jitter state files.",
    )

    sim_p = sub.add_parser("simulate", help="Simulate a jitter delay value.")
    sim_p.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of simulated delay samples to display.",
    )
    return parser


def cmd_status(args: argparse.Namespace) -> None:
    cfg = JitterConfig.from_env()
    print(f"Jitter enabled : {cfg.enabled}")
    print(f"Max seconds    : {cfg.max_seconds}")
    if cfg.seed is not None:
        print(f"Seed           : {cfg.seed}")
    else:
        print("Seed           : (random)")


def cmd_report(args: argparse.Namespace) -> None:
    state_dir = Path(args.state_dir)
    summaries = summarize_samples(state_dir)
    if not summaries:
        print(f"No jitter data found in {state_dir}")
        return
    from cronwrap.jitter_report import render_report
    print(render_report(summaries), end="")


def cmd_simulate(args: argparse.Namespace) -> None:
    cfg = JitterConfig.from_env()
    mgr = JitterManager(cfg)
    if not cfg.enabled:
        print("Jitter is disabled. All delays would be 0.0s.")
        return
    print(f"Simulating {args.runs} jitter delay(s) (max={cfg.max_seconds}s):")
    for i in range(args.runs):
        delay = mgr.delay_seconds()
        print(f"  [{i + 1}] {delay:.3f}s")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {"status": cmd_status, "report": cmd_report, "simulate": cmd_simulate}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
