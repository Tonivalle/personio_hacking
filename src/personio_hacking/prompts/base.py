from __future__ import annotations

from abc import ABC, abstractmethod


class BasePrompt(ABC):
    """Abstract base class for user confirmation prompts."""

    @abstractmethod
    def confirm(self, title: str, message: str, default: bool = True) -> bool:
        """Prompt user to confirm an action. Returns True if confirmed, False otherwise."""
        pass
