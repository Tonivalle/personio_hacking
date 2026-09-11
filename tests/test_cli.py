from __future__ import annotations

from unittest.mock import AsyncMock, patch

from personio_hacking.cli import build_parser, main


def test_cli_parser_daily_defaults():
    parser = build_parser()
    args = parser.parse_args(["daily"])
    assert args.command == "daily"
    assert args.yes is False
    assert args.config is None


def test_cli_parser_daily_flags():
    parser = build_parser()
    args = parser.parse_args(["daily", "-y", "--config", "custom.yml"])
    assert args.command == "daily"
    assert args.yes is True
    assert args.config == "custom.yml"


def test_cli_parser_backfill():
    parser = build_parser()
    args = parser.parse_args(["backfill"])
    assert args.command == "backfill"


def test_cli_parser_schedule_install():
    parser = build_parser()
    args = parser.parse_args(["schedule", "install"])
    assert args.command == "schedule"
    assert args.action == "install"


def test_cli_main_daily_invoked():
    with (
        patch("sys.argv", ["ptrack", "daily", "-y"]),
        patch("personio_hacking.cli.resolve_config_path") as mock_resolve,
        patch("personio_hacking.cli.load_config") as mock_load,
        patch("personio_hacking.cli.daily_flow", new_callable=AsyncMock) as mock_daily,
    ):
        mock_resolve.return_value = "config.yml"
        mock_cfg = object()
        mock_load.return_value = mock_cfg

        main()

        mock_resolve.assert_called_once_with(None)
        mock_load.assert_called_once_with("config.yml")
        mock_daily.assert_awaited_once_with(mock_cfg, skip_prompt=True)
