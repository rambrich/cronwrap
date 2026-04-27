"""CLI for inspecting cardinality state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.cardinality import CardinalityConfig, CardinalityManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-cardinality",
        description="Inspect output cardinality tracking state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show cardinality state for a job")
    status_p.add_argument("job", help="Job name")
    status_p.add_argument("--state-dir", default=None)

    reset_p = sub.add_parser("reset", help="Reset cardinality state for a job")
    reset_p.add_argument("job", help="Job name")
    reset_p.add_argument("--state-dir", default=None)

    return parser


def _manager(args: argparse.Namespace) -> CardinalityManager:
    cfg = CardinalityConfig.from_env()
    cfg.enabled = True
    if getattr(args, "state_dir", None):
        cfg.state_dir = args.state_dir
    return CardinalityManager(cfg, job=args.job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    p = mgr._state_path()
    if not p.exists():
        print(f"No cardinality state found for job: {args.job}")
        return
    try:
        data = json.loads(p.read_text())
    except Exception as exc:
        print(f"Error reading state: {exc}", file=sys.stderr)
        sys.exit(1)
    entries = data.get("entries", [])
    unique_hashes = {e["hash"] for e in entries}
    cfg = CardinalityConfig.from_env()
    if getattr(args, "state_dir", None):
        cfg.state_dir = args.state_dir
    print(f"Job:          {args.job}")
    print(f"Window (s):   {cfg.window_seconds}")
    print(f"Unique count: {len(unique_hashes)}")
    print(f"Max unique:   {cfg.max_unique}")
    print(f"Exceeded:     {len(unique_hashes) > cfg.max_unique}")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    mgr.reset()
    print(f"Cardinality state reset for job: {args.job}")


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
