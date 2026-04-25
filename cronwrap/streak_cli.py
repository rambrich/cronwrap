"""CLI commands for inspecting and resetting streak state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.streak import StreakConfig, StreakManager, StreakState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-streak",
        description="Inspect and manage job streak state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show streak state for a job.")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Reset streak state for a job.")
    reset_p.add_argument("job", help="Job name")

    sub.add_parser("list", help="List all tracked jobs.")
    return parser


def _manager(args: argparse.Namespace) -> StreakManager:
    cfg = StreakConfig.from_env()
    cfg.enabled = True  # allow CLI ops regardless of env flag
    return StreakManager(cfg, args.job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    path = mgr._state_path()
    if not path.exists():
        print(f"No streak state found for job: {args.job}")
        return
    state = mgr._load_state()
    print(f"Job:                  {state.job}")
    print(f"Last status:          {state.last_status or 'unknown'}")
    print(f"Consecutive failures: {state.consecutive_failures}")
    print(f"Consecutive successes:{state.consecutive_successes}")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    mgr.reset()
    print(f"Streak state reset for job: {args.job}")


def cmd_list(args: argparse.Namespace) -> None:
    cfg = StreakConfig.from_env()
    state_dir = Path(cfg.state_dir)
    if not state_dir.exists():
        print("No streak state directory found.")
        return
    files = sorted(state_dir.glob("*.json"))
    if not files:
        print("No tracked jobs.")
        return
    for f in files:
        try:
            data = json.loads(f.read_text())
            state = StreakState.from_dict(data)
            print(
                f"{state.job:<40} last={state.last_status or 'unknown':<10} "
                f"fail_streak={state.consecutive_failures} "
                f"succ_streak={state.consecutive_successes}"
            )
        except Exception:
            print(f"  (unreadable: {f.name})")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
