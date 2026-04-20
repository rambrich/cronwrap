"""CLI for inspecting metadata configuration."""
from __future__ import annotations

import argparse
import sys

from cronwrap.metadata import MetadataConfig, MetadataManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-metadata",
        description="Inspect or test run metadata collection.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show current metadata configuration")

    collect_p = sub.add_parser("collect", help="Collect and print metadata now")
    collect_p.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def cmd_status(config: MetadataConfig) -> None:
    print(f"enabled        : {config.enabled}")
    print(f"include_hostname: {config.include_hostname}")
    print(f"include_user   : {config.include_user}")
    if config.extra:
        for k, v in config.extra.items():
            print(f"extra.{k}       : {v}")
    else:
        print("extra          : (none)")


def cmd_collect(config: MetadataConfig, as_json: bool = False) -> None:
    mgr = MetadataManager(config)
    meta = mgr.collect()
    if meta is None:
        print("metadata collection is disabled")
        return
    if as_json:
        import json
        print(json.dumps(meta.to_dict(), indent=2))
    else:
        d = meta.to_dict()
        for k, v in d.items():
            print(f"{k}: {v}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = MetadataConfig.from_env()

    if args.command == "status":
        cmd_status(config)
    elif args.command == "collect":
        cmd_collect(config, as_json=getattr(args, "json", False))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
