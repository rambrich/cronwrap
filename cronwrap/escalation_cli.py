"""CLI for inspecting and resetting escalation state."""
from __future__ import annotations
import argparse
import sys
from cronwrap.escalation import EscalationConfig, EscalationManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-escalation",
        description="Inspect and manage escalation state",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    status_p = sub.add_parser("status", help="Show consecutive failure count for a command")
    status_p.add_argument("command", help="Command string to look up")

    reset_p = sub.add_parser("reset", help="Reset escalation counter for a command")
    reset_p.add_argument("command", help="Command string to reset")

    return parser


def _manager() -> EscalationManager:
    return EscalationManager(EscalationConfig.from_env())


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager()
    count = mgr.consecutive_failures(args.command)
    threshold = mgr.config.threshold
    escalated = mgr.should_escalate(args.command)
    print(f"Command   : {args.command}")
    print(f"Failures  : {count}")
    print(f"Threshold : {threshold}")
    print(f"Escalated : {'yes' if escalated else 'no'}")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager()
    mgr.reset(args.command)
    print(f"Reset escalation counter for: {args.command}")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "reset":
        cmd_reset(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
