from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

if TYPE_CHECKING:
    from personio_hacking.config import DaySchedule

# Selectors
NAV_ATTENDANCE = "[data-test-id='navsidebar-sub-attendanceCalendar']"
TIMECARD_ROW = "[data-test-id='timesheet-timecard']"
TRACKED_HOURS = "[data-test-id='tracked-vs-target-area'] time"
ROW_CHECKBOX = "button[role='checkbox']"
TRACK_BTN = "[data-test-id='timesheet-floating-actions-track']"
DIALOG = "[data-test-id='scroll-section']"
DIALOG_ADD_WORK = "[data-test-id='timecard-add-work']"
DIALOG_SAVE = "[data-test-id='timecard-save-button']"

TIMEOUT = 10_000
SHORT_TIMEOUT = 3_000


@dataclass
class DateStatus:
    target_date: date
    is_working_day: bool
    already_tracked: bool
    tracked_hours: str | None


def format_schedule_summary(schedule: DaySchedule) -> str:
    """Format work intervals for user-facing confirmation dialogs."""
    return ", ".join(str(interval) for interval in schedule.intervals)


def get_attr_date_str(target_date: date) -> str:
    """Format target_date to match Personio's timesheet datetime attribute (YYYY-MM-DD)."""
    return target_date.isoformat()


async def navigate_to_attendance(page: Page, personio_url: str) -> None:
    """Navigate directly to the Attendance calendar view."""
    attendance = page.locator(NAV_ATTENDANCE)
    await attendance.wait_for(state="attached", timeout=TIMEOUT)
    href = await attendance.get_attribute("href") or ""
    target_url = urljoin(page.url or personio_url, href)
    await page.goto(target_url)
    await page.locator(TIMECARD_ROW).first.wait_for(state="visible", timeout=TIMEOUT)


async def check_day_status(page: Page, target_date: date) -> DateStatus:
    """Inspect the timesheet row for target_date to determine tracking state."""
    attr_date = get_attr_date_str(target_date)
    row = page.locator(f"{TIMECARD_ROW}:has(time[datetime='{attr_date}'])")

    if await row.count() == 0:
        return DateStatus(
            target_date=target_date,
            is_working_day=False,
            already_tracked=False,
            tracked_hours=None,
        )

    is_weekend = await row.get_attribute("data-is-weekend") == "true"
    is_holiday = await row.get_attribute("data-is-holiday") == "true"
    is_off_day = await row.get_attribute("data-is-off-day") == "true"

    if is_weekend or is_holiday or is_off_day:
        return DateStatus(
            target_date=target_date,
            is_working_day=False,
            already_tracked=False,
            tracked_hours=None,
        )

    tracked_text: str | None = None
    try:
        raw_text = await row.locator(TRACKED_HOURS).first.inner_text(
            timeout=SHORT_TIMEOUT
        )
        tracked_text = raw_text.strip()
    except PlaywrightTimeoutError:
        pass

    already_tracked = bool(tracked_text and tracked_text != "0h")
    return DateStatus(
        target_date=target_date,
        is_working_day=True,
        already_tracked=already_tracked,
        tracked_hours=tracked_text,
    )


async def deselect_all(page: Page) -> None:
    """Click every currently checked row checkbox to clear selection."""
    checked = page.locator(f"{TIMECARD_ROW} {ROW_CHECKBOX}[aria-checked='true']")
    while await checked.count() > 0:
        await checked.first.click()


async def fill_time_input(page: Page, test_id: str, hours: str, minutes: str) -> None:
    """Fill hours and minutes spinbuttons inside a time input."""
    group = page.locator(f"[data-test-id='{test_id}']")
    hours_btn = group.locator("[role='spinbutton'][aria-label='hours']")
    minutes_btn = group.locator("[role='spinbutton'][aria-label='minutes']")

    await hours_btn.click()
    await hours_btn.fill(hours)
    await minutes_btn.click()
    await minutes_btn.fill(minutes)


async def fill_time_period(page: Page, index: int, start: str, end: str) -> None:
    """Fill start and end inputs for a dialog period row."""
    start_h, start_m = start.split(":")
    end_h, end_m = end.split(":")
    await fill_time_input(page, f"periods.{index}.start", start_h, start_m)
    await fill_time_input(page, f"periods.{index}.end", end_h, end_m)


async def fill_dialog_schedule(page: Page, schedule: DaySchedule) -> None:
    """Fill the Personio 'Track time in bulk' dialog and click save."""
    await page.locator(DIALOG).wait_for(state="visible", timeout=TIMEOUT)

    if len(schedule.intervals) >= 2:
        i0, i1 = schedule.intervals[0], schedule.intervals[1]
        await page.locator(DIALOG_ADD_WORK).click()
        await page.locator("[data-test-id='periods.2.start']").wait_for(
            state="visible", timeout=TIMEOUT
        )
        await fill_time_period(page, 0, i0.start, i0.end)  # First work slot
        await fill_time_period(page, 1, i0.end, i1.start)  # Break slot
        await fill_time_period(page, 2, i1.start, i1.end)  # Second work slot
    else:
        await fill_time_period(
            page, 0, schedule.intervals[0].start, schedule.intervals[0].end
        )

    save_btn = page.locator(DIALOG_SAVE)
    await save_btn.click()
    await page.locator(DIALOG).wait_for(state="hidden", timeout=TIMEOUT)


async def select_days_and_track(
    page: Page, days: list[date], schedule: DaySchedule
) -> None:
    """Select the specified dates in the attendance view and fill them."""
    for day in days:
        attr_date = get_attr_date_str(day)
        checkbox = page.locator(
            f"{TIMECARD_ROW}:has(time[datetime='{attr_date}']) {ROW_CHECKBOX}"
        )
        await checkbox.wait_for(state="visible", timeout=TIMEOUT)
        await checkbox.click()

    track_btn = page.locator(TRACK_BTN)
    await track_btn.wait_for(state="visible", timeout=TIMEOUT)
    await track_btn.click()

    await fill_dialog_schedule(page, schedule)
