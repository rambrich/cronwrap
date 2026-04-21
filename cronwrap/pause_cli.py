"""CLI for managing cronwrap job pause/resume state."""
from __future__ import annotations

import argparse
import sys

from cronwrap.pause import PauseConfig, PauseManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-pause",
        description="Pause or resume a cronwrap job",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # pause
    p_pause = sub.add_parser("pause", help="Pause a job")
    p_pause.add_argument("job", help="Job name")
    p_pause.add_argument("--reason", default="", help="Reason for pausing")

    # resume
    p_resume = sub.add_parser("resume", help="Resume a paused job")
    p_resume.add_argument("job", help="Job name")

    # status
    p_status = sub.add_parser("status", help="Show pause status of a job")
    p_status.add_argument("job", help="Job name")

    return parser


def _manager(job: str) -> PauseManager:
    return PauseManager(config=PauseConfig.from_env(), job_name=job)


def cmd_pause(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    state = mgr.pause(reason=args.reason)
    print(f"Job '{args.job}' paused at {state.paused_at}")
    if state.reason:
        print(f"Reason: {state.reason}")


def cmd_resume(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    if not mgr.is_paused():
        print(f"Job '{args.job}' is not currently paused.")
        return
    mgr.resume()
    print(f"Job '{args.job}' resumed.")


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    state = mgr.status()
    if state is None or not state.paused:
        print(f"Job '{args.job}' is ACTIVE (not paused).")
    else:
        print(f"Job '{args.job}' is PAUSED")
        print(f"  Since : {state.paused_at}")
        if state.reason:
            print(f"  Reason: {state.reason}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"pause": cmd_pause, "resume": cmd_resume, "status": cmd_status}
    dispatch[args.command](args)


if __name__ == "__main__":  # pragma: no cover
    main()
