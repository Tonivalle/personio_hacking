from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from personio_hacking.config import Config, DaySchedule, WorkInterval
from personio_hacking.flows import backfill_flow, daily_flow
from personio_hacking.tracker import DateStatus


@pytest.fixture
def sample_config(tmp_path):
    return Config(
        personio_url="https://company.personio.de",
        user_data_dir=tmp_path / "profile",
        schedules=[
            DaySchedule(
                days=[1, 2, 3, 4, 5],
                intervals=[WorkInterval(start="09:00", end="17:00")],
            )
        ],
        daily_prompt_time="17:30",
        prompt_type="terminal",
    )


@pytest.mark.asyncio
async def test_daily_flow_not_working_day(sample_config):
    # Sunday is weekday 7, not in schedule
    with patch("personio_hacking.flows.date") as mock_date:
        mock_date.today.return_value = date(2026, 9, 13)  # Sunday
        mock_prompt = MagicMock()

        result = await daily_flow(sample_config, prompt=mock_prompt)
        assert result is False
        mock_prompt.confirm.assert_not_called()


@pytest.mark.asyncio
async def test_daily_flow_user_declined_prompt(sample_config):
    with patch("personio_hacking.flows.date") as mock_date:
        mock_date.today.return_value = date(2026, 9, 11)  # Friday
        mock_prompt = MagicMock()
        mock_prompt.confirm.return_value = False

        result = await daily_flow(sample_config, prompt=mock_prompt)
        assert result is False
        mock_prompt.confirm.assert_called_once()


@pytest.mark.asyncio
async def test_daily_flow_approved_and_filled(sample_config):
    with (
        patch("personio_hacking.flows.date") as mock_date,
        patch("personio_hacking.flows.get_browser_session") as mock_get_session,
        patch(
            "personio_hacking.flows.ensure_logged_in", new_callable=AsyncMock
        ) as mock_login,
        patch(
            "personio_hacking.flows.navigate_to_attendance", new_callable=AsyncMock
        ) as mock_nav,
        patch(
            "personio_hacking.flows.check_day_status", new_callable=AsyncMock
        ) as mock_check,
        patch(
            "personio_hacking.flows.select_days_and_track", new_callable=AsyncMock
        ) as mock_track,
    ):
        target_day = date(2026, 9, 11)
        mock_date.today.return_value = target_day

        mock_session = MagicMock()
        mock_session.page = MagicMock()
        mock_session.close = AsyncMock()
        mock_get_session.return_value = mock_session

        mock_check.return_value = DateStatus(
            target_date=target_day,
            is_working_day=True,
            already_tracked=False,
            tracked_hours="0h",
        )

        mock_prompt = MagicMock()
        mock_prompt.confirm.return_value = True

        result = await daily_flow(sample_config, prompt=mock_prompt)
        assert result is True

        mock_login.assert_awaited_once_with(
            mock_session.page, sample_config.personio_url
        )
        mock_nav.assert_awaited_once_with(mock_session.page, sample_config.personio_url)
        mock_track.assert_awaited_once_with(
            mock_session.page, [target_day], sample_config.schedules[0]
        )
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_daily_flow_already_tracked(sample_config):
    with (
        patch("personio_hacking.flows.date") as mock_date,
        patch("personio_hacking.flows.get_browser_session") as mock_get_session,
        patch("personio_hacking.flows.ensure_logged_in", new_callable=AsyncMock),
        patch("personio_hacking.flows.navigate_to_attendance", new_callable=AsyncMock),
        patch(
            "personio_hacking.flows.check_day_status", new_callable=AsyncMock
        ) as mock_check,
        patch(
            "personio_hacking.flows.select_days_and_track", new_callable=AsyncMock
        ) as mock_track,
    ):
        target_day = date(2026, 9, 11)
        mock_date.today.return_value = target_day

        mock_session = MagicMock()
        mock_session.page = MagicMock()
        mock_session.close = AsyncMock()
        mock_get_session.return_value = mock_session

        mock_check.return_value = DateStatus(
            target_date=target_day,
            is_working_day=True,
            already_tracked=True,
            tracked_hours="8h",
        )

        result = await daily_flow(sample_config, skip_prompt=True)
        assert result is False
        mock_track.assert_not_called()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_backfill_flow(sample_config):
    with (
        patch("personio_hacking.flows.get_browser_session") as mock_get_session,
        patch(
            "personio_hacking.flows.ensure_logged_in", new_callable=AsyncMock
        ) as mock_login,
        patch(
            "personio_hacking.flows.fill_missing_days", new_callable=AsyncMock
        ) as mock_fill,
    ):
        mock_session = MagicMock()
        mock_session.page = MagicMock()
        mock_session.close = AsyncMock()
        mock_get_session.return_value = mock_session

        await backfill_flow(sample_config)

        mock_login.assert_awaited_once_with(
            mock_session.page, sample_config.personio_url
        )
        mock_fill.assert_awaited_once_with(mock_session.page, sample_config)
        mock_session.close.assert_awaited_once()
