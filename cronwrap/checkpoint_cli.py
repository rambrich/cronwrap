"""CLI for inspecting and resetting cronwrap checkpoints."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.checkpoint import CheckpointConfig, CheckpointManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cronwrap-checkpoint", description="Inspect cronwrap checkpoints")
    sub = parser.add_subparsers(dest="cmd", required=True)

    status_p = sub.add_parser("status", help="Show checkpoint for a command")
    status_p.add_argument("command", help="Command string to look up")

    reset_p = sub.add_parser("reset", help="Delete checkpoint for a command")
    reset_p.add_argument("command", help="Command string to reset")

    sub.add_parser("list", help="List all stored checkpoints")
    return parser


def _manager() -> CheckpointManager:
    cfg = CheckpointConfig.from_env()
    if not cfg.enabled:
        cfg.enabled = True  # allow CLI inspection regardless
    return CheckpointManager(cfg)


def cmd_status(args: argparse.Namespace) -> int:
    mgr = _manager()
    entry = mgr.load(args.command)
    if entry is None:
        print(f"No checkpoint found for: {args.command}")
        return 1
    print(json.dumps(entry.to_dict(), indent=2))
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    mgr = _manager()
    p = mgr._path(args.command)
    if p.exists():
        p.unlink()
        print(f"Checkpoint reset for: {args.command}")
    else:
        print(f"No checkpoint found for: {args.command}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    mgr = _manager()
    state_dir = Path(mgr.config.state_dir)
    if not state_dir.exists():
        print("No checkpoints stored.")
        return 0
    files = list(state_dir.glob("*.json"))
    if not files:
        print("No checkpoints stored.")
        return 0
    for f in sorted(files):
        print(f.stem)
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handlers = {"status": cmd_status, "reset": cmd_reset, "list": cmd_list}
    sys.exit(handlers[args.cmd](args))


if __name__ == "__main__":
    main()
