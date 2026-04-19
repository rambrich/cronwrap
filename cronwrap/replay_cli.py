"""CLI for replaying dead-letter queue entries."""
from __future__ import annotations

import argparse
import sys

from cronwrap.deadletter import DeadLetterConfig, DeadLetterManager
from cronwrap.replay import ReplayConfig, ReplayManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cronwrap-replay", description="Replay failed cron jobs")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List replayable dead-letter entries")

    run_p = sub.add_parser("run", help="Replay all (up to max) dead-letter entries")
    run_p.add_argument("--max", type=int, default=None, help="Override max replays")

    one_p = sub.add_parser("one", help="Replay a single entry by ID")
    one_p.add_argument("id", help="Entry ID to replay")

    return parser


def _manager(max_override: int | None = None) -> ReplayManager:
    cfg = ReplayConfig.from_env()
    if max_override is not None:
        cfg.max_replays = max_override
    cfg.enabled = True  # CLI always enables replay
    return ReplayManager(cfg, DeadLetterConfig.from_env())


def cmd_list(args: argparse.Namespace) -> None:
    dl = DeadLetterManager(DeadLetterConfig.from_env())
    entries = dl.list()
    if not entries:
        print("No dead-letter entries.")
        return
    for e in entries:
        print(f"{e.id}  {e.command}  failures={e.failure_count}")


def cmd_run(args: argparse.Namespace) -> None:
    mgr = _manager(getattr(args, "max", None))
    result = mgr.replay_all()
    print(f"Replayed {result.replayed}: {result.succeeded} succeeded, {result.failed} failed, {result.skipped} skipped.")


def cmd_one(args: argparse.Namespace) -> None:
    mgr = _manager()
    run = mgr.replay_one(args.id)
    if run is None:
        print(f"Entry {args.id!r} not found.")
        sys.exit(1)
    status = "OK" if run.success else "FAIL"
    print(f"[{status}] exit={run.exit_code}")
    if run.stdout:
        print(run.stdout)
    if run.stderr:
        print(run.stderr, file=sys.stderr)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {"list": cmd_list, "run": cmd_run, "one": cmd_one}
    fn = dispatch.get(args.cmd)
    if fn is None:
        parser.print_help()
        sys.exit(1)
    fn(args)


if __name__ == "__main__":
    main()
