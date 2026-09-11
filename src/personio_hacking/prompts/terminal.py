from __future__ import annotations

from personio_hacking.prompts.base import BasePrompt


class TerminalPrompt(BasePrompt):
    """Command-line text prompt using standard input."""

    def confirm(self, title: str, message: str, default: bool = True) -> bool:
        choice_hint = "[Y/n]" if default else "[y/N]"
        full_prompt = f"\n=== {title} ===\n{message}\nProceed? {choice_hint} "
        try:
            answer = input(full_prompt).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return False

        if not answer:
            return default
        return answer in {"y", "yes"}
