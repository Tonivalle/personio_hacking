from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from personio_hacking.config import DaySchedule, WorkInterval
from personio_hacking.tracker import (
    DateStatus,
    check_day_status,
    format_schedule_summary,
)


def test_format_schedule_summary():
    schedule = DaySchedule(
        days=[1, 2, 3, 4],
        intervals=[
            WorkInterval(start="09:00", end="13:00"),
            WorkInterval(start="14:00", end="18:00"),
        ],
    )
    summary = format_schedule_summary(schedule)
    assert summary == "09:00 – 13:00, 14:00 – 18:00"


@pytest.mark.asyncio
async def test_check_day_status_already_tracked():
    mock_page = MagicMock()
    mock_row = MagicMock()
    mock_row.count = AsyncMock(return_value=1)
    mock_row.get_attribute = AsyncMock(side_effect=lambda attr: "false")
    mock_tracked = MagicMock()
    mock_tracked.inner_text = AsyncMock(return_value="8h")
    mock_row.locator = MagicMock(return_value=MagicMock(first=mock_tracked))

    mock_page.locator = MagicMock(return_value=mock_row)

    status = await check_day_status(mock_page, date(2026, 9, 10))
    expected = DateStatus(
        target_date=date(2026, 9, 10),
        is_working_day=True,
        already_tracked=True,
        tracked_hours="8h",
    )
    assert status == expected


@pytest.mark.asyncio
async def test_check_day_status_untracked():
    mock_page = MagicMock()
    mock_row = MagicMock()
    mock_row.count = AsyncMock(return_value=1)
    mock_row.get_attribute = AsyncMock(side_effect=lambda attr: "false")
    mock_tracked = MagicMock()
    mock_tracked.inner_text = AsyncMock(return_value="0h")
    mock_row.locator = MagicMock(return_value=MagicMock(first=mock_tracked))

    mock_page.locator = MagicMock(return_value=mock_row)

    status = await check_day_status(mock_page, date(2026, 9, 10))
    expected = DateStatus(
        target_date=date(2026, 9, 10),
        is_working_day=True,
        already_tracked=False,
        tracked_hours="0h",
    )
    assert status == expected


@pytest.mark.asyncio
async def test_check_day_status_holiday_or_off():
    mock_page = MagicMock()
    mock_row = MagicMock()
    mock_row.count = AsyncMock(return_value=1)
    mock_row.get_attribute = AsyncMock(
        side_effect=lambda attr: "true" if attr == "data-is-holiday" else "false"
    )

    mock_page.locator = MagicMock(return_value=mock_row)

    status = await check_day_status(mock_page, date(2026, 9, 10))
    expected = DateStatus(
        target_date=date(2026, 9, 10),
        is_working_day=False,
        already_tracked=False,
        tracked_hours=None,
    )
    assert status == expected
