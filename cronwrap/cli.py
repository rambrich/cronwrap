"""CLI entry point for cronwrap."""

import argparse
import sys
import logging

from cronwrap.runner import run_command
from cronwrap.notifier import Notifier, NotifierConfig

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("cronwrap")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Wrap a cron command with logging, retries, and alerts.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run")
    parser.add_argument("--job-name", default="cron job", help="Human-readable job name")
    parser.add_argument("--retries", type=int, default=0, help="Number of retries on failure")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout in seconds")
    parser.add_argument(
        "--notify-on-success", action="store_true", help="Send alert even on success"
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = args.command
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        parser.print_help()
        return 2

    log.info("Starting job '%s': %s", args.job_name, " ".join(command))

    result = run_command(
        command,
        retries=args.retries,
        timeout=args.timeout,
    )

    if result.stdout:
        log.info("stdout:\n%s", result.stdout.rstrip())
    if result.stderr:
        log.warning("stderr:\n%s", result.stderr.rstrip())

    notifier = Notifier(NotifierConfig.from_env())

    if result.returncode != 0:
        log.error(
            "Job '%s' FAILED (exit %d) after %d attempt(s).",
            args.job_name,
            result.returncode,
            result.attempts,
        )
        notifier.notify_failure(result, job_name=args.job_name)
        return result.returncode

    log.info(
        "Job '%s' succeeded after %d attempt(s).", args.job_name, result.attempts
    )
    if args.notify_on_success:
        notifier.notify_success(result, job_name=args.job_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
