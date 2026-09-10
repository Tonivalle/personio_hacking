from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class WorkInterval:
    start: str  # "09:00"
    end: str  # "13:00"

    def __str__(self) -> str:
        return f"{self.start} – {self.end}"


@dataclass
class DaySchedule:
    days: list[int]  # ISO weekday: 1=Mon, 7=Sun
    intervals: list[WorkInterval]


@dataclass
class Config:
    personio_url: str
    user_data_dir: Path
    schedules: list[DaySchedule]
    confirm: bool = False

    def get_schedule_for_weekday(self, iso_weekday: int) -> Optional[DaySchedule]:
        for schedule in self.schedules:
            if iso_weekday in schedule.days:
                return schedule
        return None


def load_config(path: Path) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    schedules: list[DaySchedule] = []
    for s in raw.get("schedules", []):
        intervals = [
            WorkInterval(start=i["start"], end=i["end"]) for i in s["intervals"]
        ]
        schedules.append(DaySchedule(days=s["days"], intervals=intervals))

    user_data_dir = Path(raw.get("user_data_dir", "./playwright_profile"))
    # Resolve relative paths relative to the config file's directory
    if not user_data_dir.is_absolute():
        user_data_dir = (path.parent / user_data_dir).resolve()

    return Config(
        personio_url=raw["personio_url"].rstrip("/"),
        user_data_dir=user_data_dir,
        schedules=schedules,
        confirm=bool(raw.get("confirm", False)),
    )
