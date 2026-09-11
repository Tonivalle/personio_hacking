from __future__ import annotations

from datetime import date, timedelta

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from personio_hacking.config import Config
from personio_hacking.tracker import (
    SHORT_TIMEOUT,
    TIMECARD_ROW,
    TIMEOUT,
    TRACKED_HOURS,
    deselect_all,
    navigate_to_attendance,
    select_days_and_track,
)


async def fill_missing_days(page: Page, config: Config) -> None:
    """
    Scan every workday of the current month, group missing days by schedule
    (regular vs Friday), then fill each group in bulk via the Track button.
    """
    today = date.today()

    await navigate_to_attendance(page, config.personio_url)

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
            await select_days_and_track(page, regular_days, schedule)

    if fridays:
        schedule = config.get_schedule_for_weekday(5)  # Friday schedule
        if schedule:
            # Deselect any rows still checked from the previous group
            await deselect_all(page)
            print(f"Selecting {len(fridays)} Friday(s)…")
            await select_days_and_track(page, fridays, schedule)

    print("\nDone.")


async def _get_missing_workday_dates(page: Page, today: date) -> list[date]:
    """Return all workday dates visible in the timesheet that have 0h tracked."""
    rows = page.locator(TIMECARD_ROW)
    await rows.first.wait_for(state="visible", timeout=TIMEOUT)
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
            tracked_text = await row.locator(TRACKED_HOURS).first.inner_text(
                timeout=SHORT_TIMEOUT
            )
            if tracked_text.strip() == "0h":
                missing.append(row_date)
        except PlaywrightTimeoutError:
            pass

    return missing
