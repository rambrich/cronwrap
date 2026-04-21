"""CLI interface for inspecting and managing watchdog state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.watchdog import WatchdogConfig, WatchdogManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-watchdog",
        description="Inspect and manage cronwrap watchdog state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # status subcommand
    status_p = sub.add_parser("status", help="Show watchdog status for a job.")
    status_p.add_argument("job", help="Job name to inspect.")
    status_p.add_argument(
        "--state-dir",
        default=None,
        help="Directory where watchdog state files are stored.",
    )

    # reset subcommand
    reset_p = sub.add_parser("reset", help="Clear watchdog state for a job.")
    reset_p.add_argument("job", help="Job name to reset.")
    reset_p.add_argument(
        "--state-dir",
        default=None,
        help="Directory where watchdog state files are stored.",
    )

    # list subcommand
    list_p = sub.add_parser("list", help="List all jobs with watchdog state.")
    list_p.add_argument(
        "--state-dir",
        default=None,
        help="Directory where watchdog state files are stored.",
    )

    return parser


def _manager(job: str, state_dir: str | None) -> WatchdogManager:
    """Build a WatchdogManager with an optional state directory override."""
    cfg = WatchdogConfig.from_env()
    if state_dir:
        cfg = WatchdogConfig(
            enabled=cfg.enabled,
            state_dir=state_dir,
            timeout_seconds=cfg.timeout_seconds,
            alert_after=cfg.alert_after,
        )
    return WatchdogManager(cfg, job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job, getattr(args, "state_dir", None))
    state = mgr.load()
    if state is None:
        print(f"No watchdog state found for job: {args.job}")
        return
    data = state.to_dict()
    print(f"Job:          {args.job}")
    print(f"Last seen:    {data.get('last_seen', 'N/A')}")
    print(f"Consecutive:  {data.get('consecutive_failures', 0)} failure(s)")
    print(f"Alerted:      {data.get('alerted', False)}")
    print(f"Timed out:    {data.get('timed_out', False)}")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.job, getattr(args, "state_dir", None))
    path = Path(mgr._state_path())
    if path.exists():
        path.unlink()
        print(f"Watchdog state reset for job: {args.job}")
    else:
        print(f"No watchdog state found for job: {args.job}")


def cmd_list(args: argparse.Namespace) -> None:
    cfg = WatchdogConfig.from_env()
    state_dir = getattr(args, "state_dir", None) or cfg.state_dir
    base = Path(state_dir)
    if not base.exists():
        print("No watchdog state directory found.")
        return
    files = sorted(base.glob("watchdog_*.json"))
    if not files:
        print("No watchdog state files found.")
        return
    print(f"{'Job':<30}  {'Last Seen':<25}  {'Failures':>8}  {'Alerted':>8}")
    print("-" * 80)
    for f in files:
        try:
            data = json.loads(f.read_text())
            job = f.stem.replace("watchdog_", "", 1)
            last_seen = data.get("last_seen", "N/A")
            failures = data.get("consecutive_failures", 0)
            alerted = data.get("alerted", False)
            print(f"{job:<30}  {last_seen:<25}  {failures:>8}  {str(alerted):>8}")
        except Exception:
            print(f"{f.name:<30}  (unreadable)")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "status": cmd_status,
        "reset": cmd_reset,
        "list": cmd_list,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
