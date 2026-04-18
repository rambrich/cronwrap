"""CLI to test heartbeat configuration."""
from __future__ import annotations

import argparse
import sys

from cronwrap.heartbeat import HeartbeatConfig, HeartbeatManager
from cronwrap.runner import RunResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-heartbeat",
        description="Test heartbeat ping configuration",
    )
    sub = parser.add_subparsers(dest="cmd")

    ping_p = sub.add_parser("ping", help="Send a test heartbeat ping")
    ping_p.add_argument("--url", default="", help="Override heartbeat URL")
    ping_p.add_argument("--fail", action="store_true", help="Simulate a failed run")

    sub.add_parser("status", help="Show current heartbeat config from environment")
    return parser


def run_heartbeat_cli(args: argparse.Namespace) -> int:
    if args.cmd == "status":
        cfg = HeartbeatConfig.from_env()
        print(f"enabled     : {cfg.enabled}")
        print(f"url         : {cfg.url or '(not set)'}")
        print(f"on_success  : {cfg.on_success}")
        print(f"on_failure  : {cfg.on_failure}")
        print(f"timeout     : {cfg.timeout}s")
        return 0

    if args.cmd == "ping":
        cfg = HeartbeatConfig.from_env()
        if args.url:
            cfg.url = args.url
            cfg.enabled = True
            cfg.on_failure = True
        if not cfg.enabled:
            print("Heartbeat not configured. Set CRONWRAP_HEARTBEAT_URL.", file=sys.stderr)
            return 1
        success = not args.fail
        result = RunResult(
            command="test",
            returncode=0 if success else 1,
            stdout="",
            stderr="",
            duration=0.0,
            success=success,
        )
        mgr = HeartbeatManager(config=cfg)
        status = mgr.ping(result)
        if status is None:
            print("Ping skipped or failed.")
            return 1
        print(f"Ping sent. HTTP status: {status}")
        return 0

    print("No command given. Use ping or status.", file=sys.stderr)
    return 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(run_heartbeat_cli(args))


if __name__ == "__main__":
    main()
