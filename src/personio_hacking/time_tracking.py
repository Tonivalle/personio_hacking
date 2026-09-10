from __future__ import annotations

from datetime import date, timedelta

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from personio_hacking.config import Config, DaySchedule

# ---------------------------------------------------------------------------
# Selectors — update these if Personio changes its UI
# ---------------------------------------------------------------------------
# Sidebar
_NAV_PARENT = "[data-test-id='navsidebar-companyTimeline']"
_NAV_ATTENDANCE = "[data-test-id='navsidebar-sub-attendanceCalendar']"

# Attendance timesheet rows
_TIMECARD_ROW = "[data-test-id='timesheet-timecard']"
_TRACKED_HOURS = "[data-test-id='tracked-vs-target-area'] time"

# Bulk selection
_ROW_CHECKBOX = "button[role='checkbox']"
_TRACK_BTN = "[data-test-id='timesheet-floating-actions-track']"

# Bulk time-entry dialog
_DIALOG = "[data-test-id='scroll-section']"
_DIALOG_ADD_WORK = "[data-test-id='timecard-add-work']"
_DIALOG_SAVE = "[data-test-id='timecard-save-button']"

_TIMEOUT = 10_000  # ms for most waits
_SHORT_TIMEOUT = 3_000  # ms for "does this element exist?" checks


async def fill_missing_days(page: Page, config: Config) -> None:
    """
    Scan every workday of the current month, group missing days by schedule
    (regular vs Friday), then fill each group in bulk via the Track button.
    """
    today = date.today()

    await _navigate_to_time_tracking(page, config.personio_url)

    missing = await _get_missing_workday_dates(page, today)
    if not missing:
        print("All working days this month are already filled. Nothing to do.")
        return

    # Split into groups that share the same schedule
    regular_days = [d for d in missing if d.isoweekday() != 5]
    fridays = [d for d in missing if d.isoweekday() == 5]

    print(f"\nFound {len(missing)} day(s) to fill:")
    for day in missing:
        schedule = config.get_schedule_for_weekday(day.isoweekday())
        if schedule:
            print(
                f"  {day.strftime('%A, %d %b %Y')}: "
                + ", ".join(str(i) for i in schedule.intervals)
            )
    print()

    if config.confirm:
        try:
            input("Press Enter to fill all of the above, or Ctrl+C to cancel… ")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return

    if regular_days:
        schedule = config.get_schedule_for_weekday(1)  # Mon–Thu schedule
        if schedule:
            print(f"Selecting {len(regular_days)} regular day(s)…")
            await _select_days_and_track(page, regular_days, schedule)

    if fridays:
        schedule = config.get_schedule_for_weekday(5)  # Friday schedule
        if schedule:
            # Deselect any rows still checked from the previous group
            await _deselect_all(page)
            print(f"Selecting {len(fridays)} Friday(s)…")
            await _select_days_and_track(page, fridays, schedule)

    print("\nDone.")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _deselect_all(page: Page) -> None:
    """Click every currently-checked row checkbox to deselect it."""
    checked = page.locator(f"{_TIMECARD_ROW} {_ROW_CHECKBOX}[aria-checked='true']")
    # Always click .first() — the locator is live so indices shift as items are unchecked.
    while await checked.count() > 0:
        await checked.first.click()


async def _navigate_to_time_tracking(page: Page, personio_url: str) -> None:
    # The attendance link is always in the DOM (even when hidden behind the hover
    # dropdown), so we can grab its href and navigate directly — no hover needed.
    attendance = page.locator(_NAV_ATTENDANCE)
    await attendance.wait_for(state="attached", timeout=_TIMEOUT)
    href = await attendance.get_attribute("href")
    await page.goto(f"{personio_url}{href}")
    # Wait until the timesheet rows are visible before returning
    await page.locator(_TIMECARD_ROW).first.wait_for(state="visible", timeout=_TIMEOUT)


async def _get_missing_workday_dates(page: Page, today: date) -> list[date]:
    """Return all workday dates visible in the timesheet that have 0h tracked."""
    rows = page.locator(_TIMECARD_ROW)
    await rows.first.wait_for(state="visible", timeout=_TIMEOUT)
    count = await rows.count()

    missing: list[date] = []
    for i in range(count):
        row = rows.nth(i)

        if (
            await row.get_attribute("data-is-weekend") == "true"
            or await row.get_attribute("data-is-holiday") == "true"
            or await row.get_attribute("data-is-off-day") == "true"
        ):
            continue

        # Personio's datetime attribute is 0-indexed (day 0 = 1st of month),
        # so the value is always 1 day behind the displayed date.
        datetime_str = await row.locator("time[datetime]").first.get_attribute(
            "datetime"
        )
        if not datetime_str:
            continue
        try:
            row_date = date.fromisoformat(datetime_str) + timedelta(days=1)
        except ValueError:
            continue

        if row_date > today:
            continue

        try:
            tracked_text = await row.locator(_TRACKED_HOURS).first.inner_text(
                timeout=_SHORT_TIMEOUT
            )
            if tracked_text.strip() == "0h":
                missing.append(row_date)
        except PlaywrightTimeoutError:
            pass

    return missing


async def _select_days_and_track(
    page: Page, days: list[date], schedule: DaySchedule
) -> None:
    """
    Tick the checkbox on every row in *days*, then click the floating Track
    button to open the bulk time-entry UI.
    """
    for day in days:
        # Selector must use the datetime attribute value (1 day behind displayed date)
        attr_date_str = (day - timedelta(days=1)).isoformat()
        checkbox = page.locator(
            f"[data-test-id='timesheet-timecard']:has(time[datetime='{attr_date_str}'])"
            f" {_ROW_CHECKBOX}"
        )
        await checkbox.wait_for(state="visible", timeout=_TIMEOUT)
        await checkbox.click()

    track_btn = page.locator(_TRACK_BTN)
    await track_btn.wait_for(state="visible", timeout=_TIMEOUT)
    await track_btn.click()

    await _fill_bulk_schedule(page, schedule)


async def _fill_bulk_schedule(page: Page, schedule: DaySchedule) -> None:
    """
    Fill the "Track time in bulk" dialog.

    The dialog always opens with one Work row (periods.0) and one Break row
    (periods.1). Two cases:

    • 2 work intervals (Mon–Thu): click "+ Work" to add periods.2, then fill
      Work(0) → first interval, Break(1) → gap between intervals, Work(2) →
      second interval.

    • 1 work interval (Friday): just fill Work(0) and save — the Break row
      is left empty and ignored.
    """
    await page.locator(_DIALOG).wait_for(state="visible", timeout=_TIMEOUT)

    if len(schedule.intervals) >= 2:
        i0, i1 = schedule.intervals[0], schedule.intervals[1]

        # Add a second Work row — it will become periods.2
        await page.locator(_DIALOG_ADD_WORK).click()
        await page.locator("[data-test-id='periods.2.start']").wait_for(
            state="visible", timeout=_TIMEOUT
        )

        await _fill_time_period(page, 0, i0.start, i0.end)  # Work
        await _fill_time_period(page, 1, i0.end, i1.start)  # Break (gap)
        await _fill_time_period(page, 2, i1.start, i1.end)  # Work
    else:
        await _fill_time_period(
            page, 0, schedule.intervals[0].start, schedule.intervals[0].end
        )
    # Leave save commented out while testing — review in the browser before saving.
    save_btn = page.locator(_DIALOG_SAVE)
    await save_btn.click()


async def _fill_time_period(page: Page, index: int, start: str, end: str) -> None:
    """Fill the start and end spinbuttons for the period at *index*."""
    start_h, start_m = start.split(":")
    end_h, end_m = end.split(":")
    await _fill_time_input(page, f"periods.{index}.start", start_h, start_m)
    await _fill_time_input(page, f"periods.{index}.end", end_h, end_m)


async def _fill_time_input(page: Page, test_id: str, hours: str, minutes: str) -> None:
    """Click and fill the hours/minutes spinbuttons inside a time input group."""
    group = page.locator(f"[data-test-id='{test_id}']")
    hours_btn = group.locator("[role='spinbutton'][aria-label='hours']")
    minutes_btn = group.locator("[role='spinbutton'][aria-label='minutes']")

    await hours_btn.click()
    await hours_btn.fill(hours)
    await minutes_btn.click()
    await minutes_btn.fill(minutes)
