"""CLI commands for cluster state inspection."""
from __future__ import annotations

import argparse
import sys
import time

from cronwrap.cluster import ClusterConfig, ClusterManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-cluster",
        description="Inspect cluster coordination state.",
    )
    sub = parser.add_subparsers(dest="command")

    status_p = sub.add_parser("status", help="Show last-run state for a job")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Clear cluster state for a job")
    reset_p.add_argument("job", help="Job name")

    return parser


def _manager() -> ClusterManager:
    return ClusterManager(ClusterConfig.from_env())


def cmd_status(args: argparse.Namespace, mgr: ClusterManager | None = None) -> None:
    if mgr is None:
        mgr = _manager()
    state = mgr.load(args.job)
    if state is None:
        print(f"No cluster state found for job: {args.job}")
        return
    age = time.time() - state.last_run
    stale = age > mgr.config.stale_seconds
    print(f"Job       : {args.job}")
    print(f"Node      : {state.node_id}")
    print(f"Last run  : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(state.last_run))}")
    print(f"Success   : {state.success}")
    print(f"Age (s)   : {age:.1f}")
    print(f"Stale     : {stale}")


def cmd_reset(args: argparse.Namespace, mgr: ClusterManager | None = None) -> None:
    if mgr is None:
        mgr = _manager()
    path = mgr._state_path(args.job)
    if path.exists():
        path.unlink()
        print(f"Cluster state cleared for job: {args.job}")
    else:
        print(f"No state to clear for job: {args.job}")


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
