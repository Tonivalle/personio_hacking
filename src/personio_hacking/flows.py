from __future__ import annotations

from datetime import date

from personio_hacking.browser import get_browser_session
from personio_hacking.config import Config
from personio_hacking.login import ensure_logged_in
from personio_hacking.prompts import BasePrompt, get_prompt
from personio_hacking.time_tracking import fill_missing_days
from personio_hacking.tracker import (
    check_day_status,
    format_schedule_summary,
    navigate_to_attendance,
    select_days_and_track,
)


async def daily_flow(
    config: Config,
    skip_prompt: bool = False,
    prompt: BasePrompt | None = None,
) -> bool:
    """
    Check if today is a scheduled workday, prompt the user with the schedule,
    and fill today's hours in Personio upon approval.
    """
    today = date.today()
    schedule = config.get_schedule_for_weekday(today.isoweekday())
    if not schedule:
        print(f"Today ({today.strftime('%A, %d %b')}) is not a scheduled working day.")
        return False

    schedule_text = format_schedule_summary(schedule)
    day_name = today.strftime("%A, %d %b %Y")

    if not skip_prompt:
        active_prompt = prompt or get_prompt(config.prompt_type)
        title = "Personio Time Tracker"
        message = f"Track hours for today ({day_name})?\n\nSchedule: {schedule_text}"
        confirmed = active_prompt.confirm(title=title, message=message, default=True)
        if not confirmed:
            print("Tracking skipped by user.")
            return False

    print(f"Connecting to browser for {day_name} ({schedule_text})...")
    session = await get_browser_session(config)
    try:
        page = session.page
        await ensure_logged_in(page, config.personio_url)
        await navigate_to_attendance(page, config.personio_url)

        status = await check_day_status(page, today)
        if not status.is_working_day:
            print(
                "Today is marked as an off-day, holiday, or weekend in Personio. Skipping."
            )
            return False

        if status.already_tracked:
            print(f"Today already has {status.tracked_hours} tracked. Nothing to do.")
            return False

        print(f"Tracking today: {schedule_text}")
        await select_days_and_track(page, [today], schedule)
        print("Today's hours tracked successfully.")
        return True
    finally:
        await session.close()


async def backfill_flow(config: Config) -> None:
    """
    Scan all missing workdays of the current month and fill them in bulk.
    """
    print("Starting month backfill...")
    session = await get_browser_session(config)
    try:
        page = session.page
        await ensure_logged_in(page, config.personio_url)
        await fill_missing_days(page, config)
    finally:
        await session.close()
