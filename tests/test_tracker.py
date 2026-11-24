from datetime import date
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from personio_hacking.config import DaySchedule, WorkInterval
from personio_hacking.tracker import (
    DIALOG,
    DIALOG_SAVE,
    TIMECARD_ROW,
    TIMEOUT,
    DateStatus,
    check_day_status,
    fill_dialog_schedule,
    format_schedule_summary,
    get_attr_date_str,
    navigate_to_attendance,
)


def test_get_attr_date_str():
    assert get_attr_date_str(date(2026, 11, 11)) == "2026-11-11"
    assert get_attr_date_str(date(2026, 9, 10)) == "2026-09-10"


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
    mock_page.locator.assert_called_once_with(
        f"{TIMECARD_ROW}:has(time[datetime='2026-09-10'])"
    )


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


@pytest.mark.asyncio
async def test_navigate_to_attendance():
    mock_page = MagicMock()
    mock_page.url = "https://company.app.personio.com/home"

    mock_nav = MagicMock()
    mock_nav.wait_for = AsyncMock()
    mock_nav.get_attribute = AsyncMock(return_value="/attendance/employee/123")

    mock_row = MagicMock()
    mock_row.wait_for = AsyncMock()

    mock_rows = MagicMock()
    mock_rows.first = mock_row

    def locator_side_effect(selector):
        if "attendanceCalendar" in selector:
            return mock_nav
        return mock_rows

    mock_page.locator.side_effect = locator_side_effect
    mock_page.goto = AsyncMock()

    await navigate_to_attendance(mock_page, "https://company.personio.de")

    mock_page.goto.assert_awaited_once_with(
        "https://company.app.personio.com/attendance/employee/123"
    )


@pytest.mark.asyncio
async def test_fill_dialog_schedule_waits_for_dialog_hidden():
    mock_page = MagicMock()
    mock_dialog = MagicMock()
    mock_dialog.wait_for = AsyncMock()
    mock_save = MagicMock()
    mock_save.click = AsyncMock()
    mock_spin = MagicMock()
    mock_spin.click = AsyncMock()
    mock_spin.fill = AsyncMock()
    mock_input_group = MagicMock()
    mock_input_group.locator.return_value = mock_spin

    def locator_side_effect(selector):
        if selector == DIALOG:
            return mock_dialog
        if selector == DIALOG_SAVE:
            return mock_save
        return mock_input_group

    mock_page.locator.side_effect = locator_side_effect

    schedule = DaySchedule(
        days=[1],
        intervals=[WorkInterval(start="09:00", end="15:30")],
    )

    await fill_dialog_schedule(mock_page, schedule)

    mock_save.click.assert_awaited_once()
    mock_dialog.wait_for.assert_has_awaits([
        call(state="visible", timeout=TIMEOUT),
        call(state="hidden", timeout=TIMEOUT),
    ])

