from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    cdp_port: int | None = None
    cdp_url: str | None = None
    daily_prompt_time: str = "17:30"
    prompt_type: str = "auto"

    def get_schedule_for_weekday(self, iso_weekday: int) -> DaySchedule | None:
        for schedule in self.schedules:
            if iso_weekday in schedule.days:
                return schedule
        return None


def resolve_config_path(explicit_path: Path | str | None = None) -> Path:
    """
    Locates the configuration file in order of precedence:
    1. explicit_path if provided
    2. ./config.yml in current working directory
    3. ~/.config/ptrack/config.yml
    """
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Config file not found at: {explicit_path}")

    cwd_path = Path.cwd() / "config.yml"
    if cwd_path.exists():
        return cwd_path.resolve()

    user_cfg = Path.home() / ".config" / "ptrack" / "config.yml"
    if user_cfg.exists():
        return user_cfg.resolve()

    # Fallback to repo root config.yml if available
    repo_cfg = Path(__file__).resolve().parent.parent.parent / "config.yml"
    if repo_cfg.exists():
        return repo_cfg.resolve()

    raise FileNotFoundError(
        "No configuration file found. Please create 'config.yml' or copy 'config.example.yml'."
    )


def load_config(path: Path | str) -> Config:
    config_path = Path(path).expanduser().resolve()
    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    schedules: list[DaySchedule] = []
    for s in raw.get("schedules", []):
        intervals = [
            WorkInterval(start=i["start"], end=i["end"]) for i in s["intervals"]
        ]
        schedules.append(DaySchedule(days=s["days"], intervals=intervals))

    user_data_dir = Path(raw.get("user_data_dir", "./playwright_profile"))
    if not user_data_dir.is_absolute():
        user_data_dir = (config_path.parent / user_data_dir).resolve()

    cdp_port = raw.get("cdp_port")
    if cdp_port is not None:
        cdp_port = int(cdp_port)

    cdp_url = raw.get("cdp_url")
    if cdp_url is None and cdp_port is not None:
        cdp_url = f"http://localhost:{cdp_port}"

    return Config(
        personio_url=raw["personio_url"].rstrip("/"),
        user_data_dir=user_data_dir,
        schedules=schedules,
        confirm=bool(raw.get("confirm", False)),
        cdp_port=cdp_port,
        cdp_url=cdp_url,
        daily_prompt_time=str(raw.get("daily_prompt_time", "17:30")),
        prompt_type=str(raw.get("prompt_type", "auto")),
    )
