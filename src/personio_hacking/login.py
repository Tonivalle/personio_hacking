from __future__ import annotations

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# How long (ms) to wait for the user to complete SSO login manually.
_MANUAL_LOGIN_TIMEOUT_MS = 3 * 60 * 1_000  # 3 minutes
# How long to wait for the SSO button to appear on the login page.
_SSO_BUTTON_TIMEOUT_MS = 10_000

# Selector for the "Continue with SSO" button
_SSO_BUTTON = "button[data-provider='oidc'][data-action-button-secondary='true']"


async def ensure_logged_in(page: Page, personio_url: str) -> None:
    """
    Navigate to *personio_url* and ensure the session is active.

    Flow:
    1. Navigate and wait for the page to settle.
    2. Check whether the SSO button is visible (login page) or not (already in).
    3. If login is needed: click SSO and wait for the redirect back to the app.
    """
    await page.goto(personio_url, wait_until="domcontentloaded")

    # Check whether we landed on a login page by looking for the SSO button.
    sso_button = page.locator(_SSO_BUTTON)
    try:
        await sso_button.wait_for(state="visible", timeout=_SSO_BUTTON_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        # SSO button not present — we're already logged in.
        print("Already logged in.\n")
        return

    print("Login page detected. Clicking 'Continue with SSO'…")
    await sso_button.click()

    print(
        f"Waiting up to {_MANUAL_LOGIN_TIMEOUT_MS // 60_000} minutes for SSO to complete…"
    )

    # Wait until the URL settles back on the Personio app (no login/oauth in path).
    await page.wait_for_url(
        f"{personio_url}/**",
        timeout=_MANUAL_LOGIN_TIMEOUT_MS,
    )
    print("Logged in successfully.\n")
