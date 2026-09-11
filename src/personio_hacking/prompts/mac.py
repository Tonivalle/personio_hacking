from __future__ import annotations

import subprocess

from personio_hacking.prompts.base import BasePrompt


class MacPrompt(BasePrompt):
    """Native macOS dialog prompt using osascript."""

    def confirm(self, title: str, message: str, default: bool = True) -> bool:
        escaped_title = title.replace('"', '\\"')
        escaped_message = message.replace('"', '\\"')

        default_button = "Track Now" if default else "Skip"
        script = (
            f'display dialog "{escaped_message}" '
            f'with title "{escaped_title}" '
            'buttons {"Skip", "Track Now"} '
            f'default button "{default_button}" '
            "with icon note"
        )

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return False
            return "button returned:Track Now" in result.stdout
        except Exception:
            return False
