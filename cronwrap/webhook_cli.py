"""CLI for testing webhook configuration."""
from __future__ import annotations
import argparse
import sys
from cronwrap.webhook import WebhookConfig, WebhookManager
from cronwrap.runner import RunResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-webhook",
        description="Test and inspect cronwrap webhook settings",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Show current webhook configuration")

    test_p = sub.add_parser("test", help="Send a test webhook payload")
    test_p.add_argument("--url", help="Override webhook URL")
    test_p.add_argument("--success", action="store_true", default=False,
                        help="Send a success payload (default: failure)")
    return parser


def cmd_status(config: WebhookConfig) -> None:
    print(f"enabled:    {config.enabled}")
    print(f"url:        {config.url or '(not set)'}")
    print(f"on_failure: {config.on_failure}")
    print(f"on_success: {config.on_success}")
    print(f"timeout:    {config.timeout}s")
    if config.extra_headers:
        print(f"headers:    {config.extra_headers}")


def cmd_test(config: WebhookConfig, url: str | None, success: bool) -> None:
    if url:
        config.url = url
        config.enabled = True
    if not config.enabled:
        print("Webhook not configured. Set CRONWRAP_WEBHOOK_URL or pass --url.", file=sys.stderr)
        sys.exit(1)
    # force sending regardless of on_success/on_failure for test
    config.on_success = True
    config.on_failure = True
    result = RunResult(
        command="cronwrap-webhook test",
        exit_code=0 if success else 1,
        stdout="test output",
        stderr="" if success else "test error",
        success=success,
        duration=0.0,
    )
    mgr = WebhookManager(config)
    status = mgr.send(result)
    if status is not None:
        print(f"Webhook delivered. HTTP status: {status}")
    else:
        print("Webhook delivery failed.", file=sys.stderr)
        sys.exit(1)


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = WebhookConfig.from_env()
    if args.cmd == "status":
        cmd_status(config)
    elif args.cmd == "test":
        cmd_test(config, args.url, args.success)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
