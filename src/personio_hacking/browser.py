from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from personio_hacking.config import Config


@dataclass
class BrowserSession:
    """Represents an active Playwright browser session ready for automation."""

    context: BrowserContext
    page: Page
    close_callback: Callable[[], Coroutine[Any, Any, None]]

    async def close(self) -> None:
        """Clean up the browser context / connection and Playwright instance."""
        await self.close_callback()


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
        no_viewport=True,
        args=["--start-maximized"],
    )
    return context, playwright


async def get_browser_session(config: Config) -> BrowserSession:
    """
    Establish a browser session according to configuration:

    1. If `cdp_url` or `cdp_port` is set: connects to an already-open Chrome window
       via Chrome DevTools Protocol (CDP). Finds an existing Personio tab or opens a new one.
       Closing disconnects Playwright without terminating your Chrome window.

    2. Otherwise: launches a standalone persistent Chromium context using `user_data_dir`.
       Closing cleans up the context and stops Playwright.
    """
    playwright = await async_playwright().start()

    if config.cdp_url:
        browser: Browser = await playwright.chromium.connect_over_cdp(config.cdp_url)
        context = (
            browser.contexts[0] if browser.contexts else await browser.new_context()
        )

        # Check if any tab already has Personio open
        target_page: Page | None = None
        for p in context.pages:
            if config.personio_url in p.url:
                target_page = p
                break

        if target_page is None:
            target_page = (
                context.pages[0] if context.pages else await context.new_page()
            )

        async def _close_cdp() -> None:
            await browser.close()
            await playwright.stop()

        return BrowserSession(
            context=context,
            page=target_page,
            close_callback=_close_cdp,
        )

    # Fallback to persistent context
    config.user_data_dir.mkdir(parents=True, exist_ok=True)
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(config.user_data_dir),
        headless=False,
        no_viewport=True,
        args=["--start-maximized"],
    )
    page = context.pages[0] if context.pages else await context.new_page()

    async def _close_persistent() -> None:
        await context.close()
        await playwright.stop()

    return BrowserSession(
        context=context,
        page=page,
        close_callback=_close_persistent,
    )
