"""CLI for inspecting and resetting trend state."""
from __future__ import annotations

import argparse
import sys

from cronwrap.trend import TrendConfig, TrendManager
from cronwrap.trend_report import print_report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-trend",
        description="Inspect and manage cronwrap trend state",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # status
    s_status = sub.add_parser("status", help="Show trend status for a job")
    s_status.add_argument("job", help="Job name")
    s_status.add_argument(
        "--state-dir",
        default=TrendConfig().state_dir,
        help="Directory with trend state files",
    )
    s_status.add_argument(
        "--window", type=int, default=20, help="Rolling window size"
    )

    # reset
    s_reset = sub.add_parser("reset", help="Reset trend state for a job")
    s_reset.add_argument("job", help="Job name")
    s_reset.add_argument("--state-dir", default=TrendConfig().state_dir)

    # report
    s_report = sub.add_parser("report", help="Print trend report for all jobs")
    s_report.add_argument("--state-dir", default=TrendConfig().state_dir)
    s_report.add_argument("--window", type=int, default=20)

    return p


def _manager(state_dir: str) -> TrendManager:
    cfg = TrendConfig(enabled=True, state_dir=state_dir)
    return TrendManager(config=cfg)


def cmd_status(args: argparse.Namespace) -> None:
    import json as _json
    from pathlib import Path

    state_file = Path(args.state_dir) / f"{args.job}.json"
    if not state_file.exists():
        print(f"No trend data for job '{args.job}'.")
        return
    try:
        history = _json.loads(state_file.read_text())
    except Exception as exc:  # noqa: BLE001
        print(f"Error reading state: {exc}", file=sys.stderr)
        sys.exit(1)
    window_slice = history[-args.window:]
    rate = sum(window_slice) / len(window_slice) if window_slice else 1.0
    print(f"Job         : {args.job}")
    print(f"Total runs  : {len(history)}")
    print(f"Window      : {len(window_slice)} (last {args.window})")
    print(f"Success rate: {rate:.1%}")
    print(f"Degrading   : {'yes' if rate < 0.5 else 'no'}")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.state_dir)
    mgr.reset(args.job)
    print(f"Trend state reset for job '{args.job}'.")


def cmd_report(args: argparse.Namespace) -> None:
    print_report(args.state_dir, window=args.window)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {"status": cmd_status, "reset": cmd_reset, "report": cmd_report}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
