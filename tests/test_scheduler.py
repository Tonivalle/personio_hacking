from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personio_hacking.config import Config, DaySchedule, WorkInterval
from personio_hacking.scheduler.launchd import (
    PLIST_LABEL,
    generate_plist_content,
    get_launchd_status,
    install_launchd_job,
    uninstall_launchd_job,
)


@pytest.fixture
def mock_config(tmp_path: Path):
    return Config(
        personio_url="https://company.personio.de",
        user_data_dir=tmp_path / "profile",
        schedules=[
            DaySchedule(
                days=[1, 2, 3, 4, 5],
                intervals=[WorkInterval(start="09:00", end="17:00")],
            )
        ],
        daily_prompt_time="17:45",
        prompt_type="dialog",
    )


def test_generate_plist_content(mock_config: Config):
    content = generate_plist_content(
        config=mock_config,
        config_path=Path("/custom/config.yml"),
        python_bin="/Users/user/.venv/bin/python",
    )
    assert PLIST_LABEL in content
    assert "<integer>17</integer>" in content
    assert "<integer>45</integer>" in content
    assert "/Users/user/.venv/bin/python" in content
    assert "-m" in content
    assert "personio_hacking.cli" in content
    assert "daily" in content
    assert "/custom/config.yml" in content


def test_install_launchd_job(mock_config: Config, tmp_path: Path):
    target_plist = tmp_path / f"{PLIST_LABEL}.plist"

    with (
        patch(
            "personio_hacking.scheduler.launchd.get_plist_path",
            return_value=target_plist,
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)

        success = install_launchd_job(
            mock_config, config_path=Path("/path/to/config.yml")
        )
        assert success is True
        assert target_plist.exists()

        content = target_plist.read_text()
        assert "<integer>17</integer>" in content
        assert "<integer>45</integer>" in content
        mock_run.assert_called_once()
        assert "launchctl" in mock_run.call_args[0][0]
        assert "load" in mock_run.call_args[0][0]


def test_uninstall_launchd_job(tmp_path: Path):
    target_plist = tmp_path / f"{PLIST_LABEL}.plist"
    target_plist.write_text("<plist></plist>")

    with (
        patch(
            "personio_hacking.scheduler.launchd.get_plist_path",
            return_value=target_plist,
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)

        success = uninstall_launchd_job()
        assert success is True
        assert not target_plist.exists()
        mock_run.assert_called_once()
        assert "launchctl" in mock_run.call_args[0][0]
        assert "unload" in mock_run.call_args[0][0]


def test_get_launchd_status_installed(tmp_path: Path):
    target_plist = tmp_path / f"{PLIST_LABEL}.plist"
    target_plist.write_text("<plist></plist>")

    with (
        patch(
            "personio_hacking.scheduler.launchd.get_plist_path",
            return_value=target_plist,
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="12345 0 com.ptrack.daily\n"
        )
        status = get_launchd_status()
        assert status["installed"] is True
        assert status["loaded"] is True
