from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from personio_hacking.login import ensure_logged_in, is_logged_in_url


def test_is_logged_in_url_matches_app_domain():
    personio_url = "https://company.personio.de"

    # Should match app.personio.com with company subdomain
    assert is_logged_in_url(
        "https://company.app.personio.com/", personio_url
    )
    assert is_logged_in_url(
        "https://company.app.personio.com/attendance/employee/123",
        personio_url,
    )
    # Should match original domain
    assert is_logged_in_url("https://company.personio.de/", personio_url)
    assert is_logged_in_url(
        "https://company.personio.de/home", personio_url
    )


def test_is_logged_in_url_rejects_login_and_oauth():
    personio_url = "https://company.personio.de"

    # Auth portals
    assert not is_logged_in_url(
        "https://login.personio.com/u/login/identifier", personio_url
    )
    assert not is_logged_in_url(
        "https://login.company.com/oauth2/v1/authorize", personio_url
    )
    # Intermediate callback endpoints
    assert not is_logged_in_url(
        "https://company.app.personio.com/login/oauth2/code/authzero?code=123",
        personio_url,
    )
    assert not is_logged_in_url(
        "https://company.personio.de/login",
        personio_url,
    )
    # Other organizations
    assert not is_logged_in_url("https://other.app.personio.com/", personio_url)


@pytest.mark.asyncio
async def test_ensure_logged_in_sso_redirect_to_app_domain():
    personio_url = "https://company.personio.de"

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()

    mock_sso_button = MagicMock()
    mock_sso_button.wait_for = AsyncMock()
    mock_sso_button.click = AsyncMock()

    mock_page.locator.return_value = mock_sso_button
    mock_page.wait_for_url = AsyncMock()

    await ensure_logged_in(mock_page, personio_url)

    mock_page.goto.assert_awaited_once_with(personio_url, wait_until="domcontentloaded")
    mock_sso_button.wait_for.assert_awaited_once_with(state="visible", timeout=10_000)
    mock_sso_button.click.assert_awaited_once()

    # wait_for_url should be called with a callable predicate, not a rigid personio.de string
    mock_page.wait_for_url.assert_awaited_once()
    call_args = mock_page.wait_for_url.call_args
    predicate = call_args[0][0]
    assert callable(predicate)

    # Predicate must match app.personio.com redirect URL
    assert predicate("https://company.app.personio.com/") is True
    # Predicate must reject Okta / login page
    assert predicate("https://login.company.com/oauth2/v1/authorize") is False


@pytest.mark.asyncio
async def test_ensure_logged_in_already_logged_in():
    personio_url = "https://company.personio.de"

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()

    mock_sso_button = MagicMock()
    mock_sso_button.wait_for = AsyncMock(side_effect=PlaywrightTimeoutError("Timeout"))

    mock_page.locator.return_value = mock_sso_button
    mock_page.wait_for_url = AsyncMock()

    await ensure_logged_in(mock_page, personio_url)

    mock_page.goto.assert_awaited_once_with(personio_url, wait_until="domcontentloaded")
    mock_page.wait_for_url.assert_not_called()
