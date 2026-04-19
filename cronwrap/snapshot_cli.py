"""CLI for inspecting snapshot state."""
from __future__ import annotations
import argparse
import json
import os
import sys
from cronwrap.snapshot import SnapshotConfig, SnapshotManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cronwrap-snapshot",
                                     description="Inspect cronwrap output snapshots")
    sub = parser.add_subparsers(dest="command")

    show = sub.add_parser("show", help="Show snapshot for a job")
    show.add_argument("job_name", help="Job name")

    sub.add_parser("list", help="List all snapshot files")

    reset = sub.add_parser("reset", help="Delete snapshot for a job")
    reset.add_argument("job_name", help="Job name")

    return parser


def _manager() -> SnapshotManager:
    return SnapshotManager(SnapshotConfig.from_env())


def cmd_show(args: argparse.Namespace) -> None:
    mgr = _manager()
    entry = mgr.load(args.job_name)
    if entry is None:
        print(f"No snapshot found for job: {args.job_name}")
        sys.exit(1)
    print(json.dumps(entry.to_dict(), indent=2))


def cmd_list(args: argparse.Namespace) -> None:
    config = SnapshotConfig.from_env()
    state_dir = config.state_dir
    if not os.path.isdir(state_dir):
        print("No snapshots directory found.")
        return
    files = [f for f in os.listdir(state_dir) if f.endswith(".json")]
    if not files:
        print("No snapshots recorded.")
        return
    for f in sorted(files):
        print(f.replace(".json", ""))


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager()
    path = mgr._state_path(args.job_name)
    if os.path.exists(path):
        os.remove(path)
        print(f"Snapshot reset for: {args.job_name}")
    else:
        print(f"No snapshot found for: {args.job_name}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "show":
        cmd_show(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
