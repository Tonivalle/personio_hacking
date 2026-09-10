from __future__ import annotations

from pathlib import Path

from playwright.async_api import BrowserContext, Playwright, async_playwright


async def create_context(user_data_dir: Path) -> tuple[BrowserContext, Playwright]:
    """
    Launch a persistent Chromium context backed by *user_data_dir*.

    Using a persistent profile means the login session (cookies) is saved to
    disk, so Okta authentication is only needed on the very first run (or after
    a session expiry).
    """
    user_data_dir.mkdir(parents=True, exist_ok=True)

    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=False,
        # no_viewport keeps the browser at the OS window size
        no_viewport=True,
        args=["--start-maximized"],
    )
    return context, playwright
