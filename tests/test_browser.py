from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from personio_hacking.browser import BrowserSession, get_browser_session
from personio_hacking.config import Config


@pytest.mark.asyncio
async def test_get_browser_session_cdp_reuses_matching_tab():
    config = Config(
        personio_url="https://company.personio.de",
        user_data_dir=Path("./profile"),
        schedules=[],
        cdp_port=9222,
        cdp_url="http://localhost:9222",
    )

    mock_existing_page = MagicMock()
    mock_existing_page.url = "https://company.personio.de/attendance"

    mock_context = MagicMock()
    mock_context.pages = [mock_existing_page]

    mock_browser = MagicMock()
    mock_browser.contexts = [mock_context]
    mock_browser.close = AsyncMock()

    mock_playwright = MagicMock()
    mock_playwright.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)
    mock_playwright.stop = AsyncMock()

    with patch("personio_hacking.browser.async_playwright") as mock_ap:
        mock_ap.return_value.start = AsyncMock(return_value=mock_playwright)

        session = await get_browser_session(config)

        assert isinstance(session, BrowserSession)
        assert session.context == mock_context
        assert session.page == mock_existing_page

        # When connected via CDP, closing should disconnect without killing user's browser
        await session.close()
        mock_browser.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_browser_session_persistent_profile():
    config = Config(
        personio_url="https://company.personio.de",
        user_data_dir=Path("./profile"),
        schedules=[],
        cdp_port=None,
        cdp_url=None,
    )

    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    mock_context.close = AsyncMock()

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch_persistent_context = AsyncMock(
        return_value=mock_context
    )
    mock_playwright.stop = AsyncMock()

    with patch("personio_hacking.browser.async_playwright") as mock_ap:
        mock_ap.return_value.start = AsyncMock(return_value=mock_playwright)

        session = await get_browser_session(config)

        assert isinstance(session, BrowserSession)
        assert session.context == mock_context
        assert session.page == mock_page

        await session.close()
        mock_context.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()
