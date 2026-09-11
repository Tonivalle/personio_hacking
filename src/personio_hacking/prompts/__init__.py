from __future__ import annotations

import platform

from personio_hacking.prompts.base import BasePrompt
from personio_hacking.prompts.mac import MacPrompt
from personio_hacking.prompts.terminal import TerminalPrompt


def get_prompt(prompt_type: str = "auto") -> BasePrompt:
    """
    Factory returning appropriate prompt implementation.

    - "dialog": MacPrompt (or TerminalPrompt if not on macOS)
    - "terminal": TerminalPrompt
    - "auto": MacPrompt on Darwin (macOS), TerminalPrompt otherwise
    """
    mode = prompt_type.lower()
    is_mac = platform.system() == "Darwin"

    if mode == "dialog":
        return MacPrompt() if is_mac else TerminalPrompt()
    elif mode == "terminal":
        return TerminalPrompt()
    else:  # "auto"
        return MacPrompt() if is_mac else TerminalPrompt()


__all__ = ["BasePrompt", "MacPrompt", "TerminalPrompt", "get_prompt"]
