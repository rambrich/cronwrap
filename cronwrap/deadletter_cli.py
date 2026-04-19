"""CLI for inspecting and managing the dead-letter queue."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from cronwrap.deadletter import DeadLetterConfig, DeadLetterQueue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-deadletter",
        description="Inspect and manage failed runs in the dead-letter queue.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List dead-letter entries")

    show = sub.add_parser("show", help="Show a specific entry by index")
    show.add_argument("index", type=int, help="Zero-based index of the entry")

    sub.add_parser("clear", help="Remove all dead-letter entries")
    return parser


def cmd_list(queue: DeadLetterQueue) -> None:
    entries = queue.list_entries()
    if not entries:
        print("No dead-letter entries.")
        return
    print(f"{'#':<4} {'Timestamp':<22} {'Exit':>4}  Command")
    print("-" * 60)
    for i, e in enumerate(entries):
        ts = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        cmd = e.command[:40] + "..." if len(e.command) > 40 else e.command
        print(f"{i:<4} {ts:<22} {e.exit_code:>4}  {cmd}")


def cmd_show(queue: DeadLetterQueue, index: int) -> None:
    entries = queue.list_entries()
    if index < 0 or index >= len(entries):
        print(f"Error: index {index} out of range (0-{len(entries)-1}).")
        sys.exit(1)
    e = entries[index]
    ts = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Timestamp : {ts}")
    print(f"Command   : {e.command}")
    print(f"Exit code : {e.exit_code}")
    print(f"Duration  : {e.duration:.2f}s")
    if e.stdout:
        print(f"--- stdout ---\n{e.stdout}")
    if e.stderr:
        print(f"--- stderr ---\n{e.stderr}")


def cmd_clear(queue: DeadLetterQueue) -> None:
    removed = queue.clear()
    print(f"Removed {removed} dead-letter entries.")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = DeadLetterConfig.from_env()
    if not config.enabled:
        print("Dead-letter queue is disabled. Set CRONWRAP_DEADLETTER_ENABLED=1 to enable.")
        sys.exit(0)
    queue = DeadLetterQueue(config)
    if args.command == "list":
        cmd_list(queue)
    elif args.command == "show":
        cmd_show(queue, args.index)
    elif args.command == "clear":
        cmd_clear(queue)


if __name__ == "__main__":
    main()
