from __future__ import annotations

import asyncio
from pathlib import Path

from personio_hacking.browser import create_context
from personio_hacking.config import load_config
from personio_hacking.login import ensure_logged_in
from personio_hacking.time_tracking import fill_missing_days

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yml"


async def _run() -> None:
    config = load_config(_CONFIG_PATH)

    context, playwright = await create_context(config.user_data_dir)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await ensure_logged_in(page, config.personio_url)
        await fill_missing_days(page, config)
    finally:
        await context.close()
        await playwright.stop()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
