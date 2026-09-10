from pathlib import Path

from personio_hacking.config import Config, DaySchedule, WorkInterval, load_config


def test_load_config_basic(tmp_path: Path):
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("""
personio_url: https://mycompany.personio.de
user_data_dir: ./browser_data
daily_prompt_time: "18:00"
prompt_type: "terminal"
schedules:
  - days: [1, 2, 3, 4]
    intervals:
      - {start: "09:00", end: "13:00"}
      - {start: "14:00", end: "18:00"}
  - days: [5]
    intervals:
      - {start: "09:00", end: "15:00"}
""")
    config = load_config(cfg_file)

    expected = Config(
        personio_url="https://mycompany.personio.de",
        user_data_dir=(tmp_path / "browser_data").resolve(),
        schedules=[
            DaySchedule(
                days=[1, 2, 3, 4],
                intervals=[
                    WorkInterval(start="09:00", end="13:00"),
                    WorkInterval(start="14:00", end="18:00"),
                ],
            ),
            DaySchedule(
                days=[5],
                intervals=[WorkInterval(start="09:00", end="15:00")],
            ),
        ],
        confirm=False,
        cdp_port=None,
        cdp_url=None,
        daily_prompt_time="18:00",
        prompt_type="terminal",
    )
    assert config == expected

    # Check schedule helper
    mon_sched = config.get_schedule_for_weekday(1)
    assert mon_sched == DaySchedule(
        days=[1, 2, 3, 4],
        intervals=[
            WorkInterval(start="09:00", end="13:00"),
            WorkInterval(start="14:00", end="18:00"),
        ],
    )

    fri_sched = config.get_schedule_for_weekday(5)
    assert fri_sched == DaySchedule(
        days=[5],
        intervals=[WorkInterval(start="09:00", end="15:00")],
    )

    assert config.get_schedule_for_weekday(7) is None


def test_load_config_with_cdp(tmp_path: Path):
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("""
personio_url: https://mycompany.personio.de
cdp_port: 9222
schedules: []
""")
    config = load_config(cfg_file)

    expected = Config(
        personio_url="https://mycompany.personio.de",
        user_data_dir=(tmp_path / "playwright_profile").resolve(),
        schedules=[],
        confirm=False,
        cdp_port=9222,
        cdp_url="http://localhost:9222",
        daily_prompt_time="17:30",
        prompt_type="auto",
    )
    assert config == expected
