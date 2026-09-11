from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from personio_hacking.config import Config

PLIST_LABEL = "com.ptrack.daily"


def get_plist_path() -> Path:
    """Return the location of the user LaunchAgents plist."""
    return Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"


def parse_prompt_time(time_str: str) -> tuple[int, int]:
    """Parse HH:MM string into (hour, minute). Defaults to 17:30 on invalid format."""
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 17, 30


def generate_plist_content(
    config: Config,
    config_path: Path,
    python_bin: str | None = None,
) -> str:
    """Generate the XML plist definition for macOS launchd."""
    hour, minute = parse_prompt_time(config.daily_prompt_time)
    executable = python_bin or sys.executable

    scheduled_days: set[int] = set()
    for s in config.schedules:
        for d in s.days:
            scheduled_days.add(d)

    if not scheduled_days:
        scheduled_days = {1, 2, 3, 4, 5}

    calendar_intervals: list[dict[str, int]] = [
        {"Weekday": day, "Hour": hour, "Minute": minute}
        for day in sorted(scheduled_days)
    ]

    plist_data: dict[str, Any] = {
        "Label": PLIST_LABEL,
        "ProgramArguments": [
            executable,
            "-m",
            "personio_hacking.cli",
            "daily",
            "--config",
            str(config_path.resolve()),
        ],
        "StartCalendarInterval": calendar_intervals,
        "StandardOutPath": "/tmp/ptrack_daily.log",
        "StandardErrorPath": "/tmp/ptrack_daily.error.log",
    }

    return plistlib.dumps(plist_data).decode("utf-8")


def install_launchd_job(config: Config, config_path: Path) -> bool:
    """Write the launchd plist file and load it with launchctl."""
    plist_path = get_plist_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    # Unload any previously loaded job first
    if plist_path.exists():
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True,
            check=False,
        )

    content = generate_plist_content(config, config_path)
    plist_path.write_text(content)

    load_res = subprocess.run(
        ["launchctl", "load", str(plist_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return load_res.returncode == 0


def uninstall_launchd_job() -> bool:
    """Unload the job with launchctl and remove the plist file."""
    plist_path = get_plist_path()
    if not plist_path.exists():
        return True

    subprocess.run(
        ["launchctl", "unload", str(plist_path)],
        capture_output=True,
        check=False,
    )
    try:
        plist_path.unlink()
        return True
    except OSError:
        return False


def get_launchd_status() -> dict[str, bool]:
    """Check if the launchd job is installed on disk and active in launchctl."""
    plist_path = get_plist_path()
    installed = plist_path.exists()
    loaded = False

    res = subprocess.run(
        ["launchctl", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0 and PLIST_LABEL in res.stdout:
        loaded = True

    return {"installed": installed, "loaded": loaded}


def handle_schedule_command(config: Config, action: str) -> None:
    """Handle CLI actions: install, uninstall, status."""
    from personio_hacking.config import resolve_config_path

    config_path = resolve_config_path()

    if action == "install":
        print(
            f"Installing launchd job to trigger daily at {config.daily_prompt_time}..."
        )
        ok = install_launchd_job(config, config_path)
        if ok:
            print(f"Successfully scheduled daily tracking ({PLIST_LABEL}).")
            print("Logs: /tmp/ptrack_daily.log")
        else:
            print("Failed to load launchd job. Check system permissions.")

    elif action == "uninstall":
        print(f"Removing scheduled job ({PLIST_LABEL})...")
        ok = uninstall_launchd_job()
        if ok:
            print("Successfully uninstalled schedule.")
        else:
            print("Failed to remove plist file.")

    elif action == "status":
        status = get_launchd_status()
        installed_str = "Yes" if status["installed"] else "No"
        loaded_str = "Yes" if status["loaded"] else "No"
        print(f"Schedule Status ({PLIST_LABEL}):")
        print(f"  Installed in LaunchAgents: {installed_str}")
        print(f"  Loaded in launchctl:       {loaded_str}")
        print(f"  Configured trigger time:   {config.daily_prompt_time}")
