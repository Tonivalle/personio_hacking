from __future__ import annotations

import argparse
import asyncio
import sys

from personio_hacking.config import load_config, resolve_config_path
from personio_hacking.flows import backfill_flow, daily_flow


def build_parser() -> argparse.ArgumentParser:
    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument(
        "--config",
        "-c",
        dest="config",
        help="Path to configuration file (defaults to config.yml or ~/.config/ptrack/config.yml)",
    )

    parser = argparse.ArgumentParser(
        prog="ptrack",
        description="Automated time tracking for Personio",
        parents=[common_parent],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # daily subcommand
    daily_parser = subparsers.add_parser(
        "daily",
        parents=[common_parent],
        help="Check today and track working hours (prompts with schedule unless --yes is passed)",
    )
    daily_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip prompt and fill today automatically if it is a working day",
    )

    # backfill subcommand
    subparsers.add_parser(
        "backfill",
        parents=[common_parent],
        help="Scan and fill missing working days for the current month",
    )

    # schedule subcommand
    schedule_parser = subparsers.add_parser(
        "schedule",
        parents=[common_parent],
        help="Manage automated daily scheduled tracking (macOS launchd)",
    )
    schedule_parser.add_argument(
        "action",
        choices=["install", "uninstall", "status"],
        help="Action to perform on the system scheduler",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_path = resolve_config_path(args.config)
    config = load_config(config_path)

    if args.command == "daily":
        asyncio.run(daily_flow(config, skip_prompt=bool(args.yes)))
    elif args.command == "backfill":
        asyncio.run(backfill_flow(config))
    elif args.command == "schedule":
        from personio_hacking.scheduler.launchd import handle_schedule_command

        handle_schedule_command(config, args.action)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
