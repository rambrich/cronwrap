"""CLI commands for inspecting and resetting quota state."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from cronwrap.quota import QuotaConfig, QuotaManager
from cronwrap.quota_report import print_report

_DEFAULT_STATE_DIR = os.environ.get("CRONWRAP_STATE_DIR", "/tmp/cronwrap")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-quota",
        description="Inspect and manage cronwrap quota state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    st = sub.add_parser("status", help="Show quota status for a job")
    st.add_argument("job", help="Job name")
    st.add_argument("--state-dir", default=_DEFAULT_STATE_DIR)

    rs = sub.add_parser("reset", help="Reset quota counters for a job")
    rs.add_argument("job", help="Job name")
    rs.add_argument("--state-dir", default=_DEFAULT_STATE_DIR)

    rp = sub.add_parser("report", help="Print quota usage report")
    rp.add_argument("--state-dir", default=_DEFAULT_STATE_DIR)

    return parser


def _manager(job: str, state_dir: str) -> QuotaManager:
    cfg = QuotaConfig.from_env()
    return QuotaManager(cfg, job=job, state_dir=state_dir)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job, args.state_dir)
    state_path = Path(args.state_dir) / f"quota_{args.job}.json"
    if not state_path.exists():
        print(f"No quota state found for job '{args.job}'.")
        return
    data = json.loads(state_path.read_text())
    limit = data.get("limit", "?")
    count = data.get("count", 0)
    window = data.get("window_seconds", "?")
    print(f"Job      : {args.job}")
    print(f"Count    : {count}")
    print(f"Limit    : {limit}")
    print(f"Window   : {window}s")
    status = "EXHAUSTED" if isinstance(limit, int) and count >= limit else "ok"
    print(f"Status   : {status}")


def cmd_reset(args: argparse.Namespace) -> None:
    state_path = Path(args.state_dir) / f"quota_{args.job}.json"
    if state_path.exists():
        state_path.unlink()
        print(f"Quota state reset for job '{args.job}'.")
    else:
        print(f"No quota state found for job '{args.job}'.")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    elif args.command == "report":
        print_report(args.state_dir)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
